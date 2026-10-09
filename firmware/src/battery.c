#include "battery.h"

#include <zephyr/drivers/adc.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(battery, LOG_LEVEL_INF);

static const struct adc_dt_spec vdd = ADC_DT_SPEC_GET(DT_PATH(zephyr_user));

int battery_init(void)
{
	if (!adc_is_ready_dt(&vdd)) {
		return -ENODEV;
	}
	return adc_channel_setup_dt(&vdd);
}

int battery_mv(void)
{
	int16_t raw;
	struct adc_sequence seq = {
		.buffer = &raw,
		.buffer_size = sizeof(raw),
	};
	int err;

	err = adc_sequence_init_dt(&vdd, &seq);
	if (err) {
		return err;
	}
	err = adc_read_dt(&vdd, &seq);
	if (err) {
		return err;
	}

	int32_t mv = raw;

	err = adc_raw_to_millivolts_dt(&vdd, &mv);
	if (err) {
		return err;
	}
	return mv;
}
