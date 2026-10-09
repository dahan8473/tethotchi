#pragma once

#include <stdint.h>

/*
 * Bump PET_SAVE_VERSION whenever this struct changes, and add a migration
 * step in pet_save.c so pets saved by older firmware keep working.
 * Only append fields; never reorder or remove.
 */
#define PET_SAVE_VERSION 1

struct pet_save {
	uint16_t version;
	uint32_t boot_count;
};

extern struct pet_save pet;

int pet_save_load(void);
int pet_save_write(void);
