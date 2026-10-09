#include "battery.h"
#include "pet_save.h"
#include "update_mode.h"

#include <app_version.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/dfu/mcuboot.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/reboot.h>

LOG_MODULE_REGISTER(main, LOG_LEVEL_INF);

/* Change this between versions to see an update land: v1.0 blinks slowly. */
#define BLINK_MS 1000

static const struct gpio_dt_spec led = GPIO_DT_SPEC_GET(DT_ALIAS(led0), gpios);

/*
 * After an update, MCUboot runs the new image once in "test" mode. If we
 * reboot without confirming, MCUboot restores the previous image. Only
 * confirm once everything needed for the *next* update works, so a release
 * that breaks Bluetooth can never strand a pet.
 */
static void confirm_or_revert(bool healthy)
{
	if (boot_is_img_confirmed()) {
		return;
	}
	if (!healthy) {
		LOG_ERR("Self-test failed, reverting to previous firmware");
		k_sleep(K_MSEC(100));
		sys_reboot(SYS_REBOOT_COLD);
	}
	if (boot_write_img_confirmed()) {
		LOG_ERR("Could not confirm image");
		return;
	}
	LOG_INF("New firmware confirmed");
}

int main(void)
{
	bool healthy = true;
	int err;

	LOG_INF("Tethos Pet v%s", APP_VERSION_STRING);

	err = pet_save_load();
	if (err) {
		LOG_ERR("Save load failed (%d)", err);
		healthy = false;
	}

	err = battery_init();
	if (err) {
		LOG_ERR("Battery ADC failed (%d)", err);
		healthy = false;
	}

	err = bt_enable(NULL);
	if (err) {
		LOG_ERR("Bluetooth failed (%d)", err);
		healthy = false;
	}

	err = update_mode_init();
	if (err) {
		LOG_ERR("Update mode init failed (%d)", err);
		healthy = false;
	}

	confirm_or_revert(healthy);

	pet.boot_count++;
	pet_save_write();
	LOG_INF("Boot #%u, save v%u", pet.boot_count, pet.version);

	gpio_pin_configure_dt(&led, GPIO_OUTPUT_INACTIVE);
	while (1) {
		gpio_pin_toggle_dt(&led);
		k_sleep(K_MSEC(BLINK_MS));
	}
	return 0;
}
