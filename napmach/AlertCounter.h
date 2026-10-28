#pragma once
#include <stdint.h>

struct AlertCounter {
  uint32_t count;
  bool active;
};

// Invalid readings preserve the episode until a valid normal reading rearms it.
constexpr AlertCounter advanceAlertCounter(AlertCounter previous, bool valid, bool exceeded) {
  return !valid ? previous : AlertCounter{
    previous.count + ((exceeded && !previous.active && previous.count < UINT32_MAX) ? 1u : 0u),
    exceeded
  };
}
