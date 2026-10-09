#include "pet_save.h"

#include <string.h>
#include <zephyr/logging/log.h>
#include <zephyr/settings/settings.h>

LOG_MODULE_REGISTER(pet_save, LOG_LEVEL_INF);

struct pet_save pet;

static int pet_set(const char *key, size_t len, settings_read_cb read_cb, void *cb_arg)
{
	if (strcmp(key, "save") != 0) {
		return -ENOENT;
	}

	/* An older save may be shorter than the current struct; new fields keep their defaults. */
	ssize_t n = read_cb(cb_arg, &pet, MIN(len, sizeof(pet)));

	return n < 0 ? (int)n : 0;
}

SETTINGS_STATIC_HANDLER_DEFINE(pet, "pet", NULL, pet_set, NULL, NULL);

static void migrate(void)
{
	if (pet.version == PET_SAVE_VERSION) {
		return;
	}
	LOG_INF("Migrating save v%u -> v%u", pet.version, PET_SAVE_VERSION);

	/* Add one block per version, e.g.:
	 * if (pet.version < 2) { pet.new_field = DEFAULT; }
	 */

	pet.version = PET_SAVE_VERSION;
}

int pet_save_load(void)
{
	int err;

	memset(&pet, 0, sizeof(pet));
	pet.version = PET_SAVE_VERSION;

	err = settings_subsys_init();
	if (err) {
		return err;
	}
	err = settings_load_subtree("pet");
	if (err) {
		return err;
	}
	migrate();
	return 0;
}

int pet_save_write(void)
{
	return settings_save_one("pet/save", &pet, sizeof(pet));
}
