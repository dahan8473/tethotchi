#include "update_mode.h"
#include "battery.h"

#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(update_mode, LOG_LEVEL_INF);

#define HOLD_MS        3000
#define POLL_MS        100
#define WINDOW_SECONDS 120
#define MIN_BATTERY_MV 2700

/* MCUmgr SMP service, advertised so the web page can filter for it */
#define SMP_SERVICE_UUID \
	BT_UUID_128_ENCODE(0x8d53dc1d, 0x1db7, 0x4cd3, 0x868b, 0x8a527460aa84)

static const struct gpio_dt_spec button_a = GPIO_DT_SPEC_GET(DT_NODELABEL(button_a), gpios);
static const struct gpio_dt_spec button_c = GPIO_DT_SPEC_GET(DT_NODELABEL(button_c), gpios);
static const struct gpio_dt_spec led_update = GPIO_DT_SPEC_GET(DT_ALIAS(led2), gpios);

static const struct bt_data ad[] = {
	BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
	BT_DATA_BYTES(BT_DATA_UUID128_ALL, SMP_SERVICE_UUID),
};

static const struct bt_data sd[] = {
	BT_DATA(BT_DATA_NAME_COMPLETE, CONFIG_BT_DEVICE_NAME, sizeof(CONFIG_BT_DEVICE_NAME) - 1),
};

static bool active;
static bool connected;
static uint32_t held_ms;

static void poll_handler(struct k_work *work);
static void window_expired(struct k_work *work);
static void restart_adv(struct k_work *work);

static K_WORK_DELAYABLE_DEFINE(poll_work, poll_handler);
static K_WORK_DELAYABLE_DEFINE(window_work, window_expired);
static K_WORK_DEFINE(adv_work, restart_adv);

static int start_adv(void)
{
	int err = bt_le_adv_start(BT_LE_ADV_CONN_FAST_1, ad, ARRAY_SIZE(ad), sd, ARRAY_SIZE(sd));

	if (err && err != -EALREADY) {
		LOG_ERR("Advertising failed (%d)", err);
	}
	return err;
}

static void enter(void)
{
	int mv = battery_mv();

	if (mv >= 0 && mv < MIN_BATTERY_MV) {
		/* TODO: show "battery low" on the screen once the display driver exists */
		LOG_WRN("Battery too low for update: %d mV", mv);
		return;
	}

	if (start_adv() && !connected) {
		return;
	}
	active = true;
	gpio_pin_set_dt(&led_update, 1);
	k_work_reschedule(&window_work, K_SECONDS(WINDOW_SECONDS));
	LOG_INF("Update mode on (%d mV)", mv);
}

static void leave(void)
{
	active = false;
	bt_le_adv_stop();
	gpio_pin_set_dt(&led_update, 0);
	LOG_INF("Update mode off");
}

static void window_expired(struct k_work *work)
{
	/* Never cut off an upload in progress; the window only closes while idle. */
	if (connected) {
		k_work_reschedule(&window_work, K_SECONDS(WINDOW_SECONDS));
		return;
	}
	leave();
}

static void restart_adv(struct k_work *work)
{
	if (active && !connected) {
		start_adv();
	}
}

static void poll_handler(struct k_work *work)
{
	bool both = gpio_pin_get_dt(&button_a) > 0 && gpio_pin_get_dt(&button_c) > 0;

	if (!both) {
		held_ms = 0;
	} else if (held_ms < HOLD_MS) {
		held_ms += POLL_MS;
		if (held_ms >= HOLD_MS && !active) {
			enter();
		}
	}
	k_work_reschedule(&poll_work, K_MSEC(POLL_MS));
}

static void on_connected(struct bt_conn *conn, uint8_t err)
{
	if (!err) {
		connected = true;
	}
}

static void on_disconnected(struct bt_conn *conn, uint8_t reason)
{
	connected = false;
	/* The browser reconnects on its own if the link drops mid-upload; keep advertising for it. */
	if (active) {
		k_work_submit(&adv_work);
		k_work_reschedule(&window_work, K_SECONDS(WINDOW_SECONDS));
	}
}

BT_CONN_CB_DEFINE(conn_callbacks) = {
	.connected = on_connected,
	.disconnected = on_disconnected,
};

int update_mode_init(void)
{
	int err;

	if (!gpio_is_ready_dt(&button_a) || !gpio_is_ready_dt(&button_c) ||
	    !gpio_is_ready_dt(&led_update)) {
		return -ENODEV;
	}
	err = gpio_pin_configure_dt(&button_a, GPIO_INPUT);
	if (err) {
		return err;
	}
	err = gpio_pin_configure_dt(&button_c, GPIO_INPUT);
	if (err) {
		return err;
	}
	err = gpio_pin_configure_dt(&led_update, GPIO_OUTPUT_INACTIVE);
	if (err) {
		return err;
	}
	k_work_reschedule(&poll_work, K_MSEC(POLL_MS));
	return 0;
}
