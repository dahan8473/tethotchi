#pragma once

/* Returns supply voltage in mV, or a negative errno. */
int battery_init(void);
int battery_mv(void);
