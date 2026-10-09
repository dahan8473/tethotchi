cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(tethos_pet)

target_sources(app PRIVATE
  src/main.c
  src/update_mode.c
  src/battery.c
  src/pet_save.c
)
