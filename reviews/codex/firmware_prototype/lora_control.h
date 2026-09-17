#ifndef LORA_CONTROL_H
#define LORA_CONTROL_H

#include <stddef.h>
#include <stdint.h>

/* Review-only reference. No HAL, PWM, radio authentication or remote arm code. */
#define RC_MAX_LINE_BYTES 127u

typedef enum { RC_THRUST, RC_RUDDER } rc_kind;
typedef struct { rc_kind kind; uint8_t value; } rc_command;
typedef enum {
    RC_PARSE_OK, RC_PARSE_FORMAT, RC_PARSE_SENDER,
    RC_PARSE_LENGTH, RC_PARSE_COMMAND, RC_PARSE_VALUE
} rc_parse_result;

/* Byte count excludes a C NUL terminator; CR, LF or CRLF suffix is optional.
 * On error, *out is unchanged. Accepts +RCV only and exact payload length.
 * expected_sender is an address filter, NOT authentication. */
rc_parse_result rc_parse(const char *line, size_t len,
                         uint16_t expected_sender, rc_command *out);

typedef enum { RC_DISARMED, RC_ARMED, RC_FAILSAFE } rc_mode;
typedef enum { RC_NO_FAULT, RC_LINK_EXPIRED, RC_EXTERNAL_FAULT,
               RC_BAD_CONFIG } rc_fault;
typedef struct {
    rc_mode mode;
    rc_fault fault;
    uint16_t expected_sender;
    uint32_t timeout_ms;
    uint32_t received_at[2];
    uint8_t seen[2];
    uint8_t requested[2];
    uint8_t thrust;
    uint8_t rudder;
} rc_control;

/* Single owner: call all state APIs from one task, never concurrently/ISR.
 * All times are the same monotonic uint32 millisecond clock. Service at least
 * once per timeout; neither stored timestamps nor caller scheduling may span
 * a full 2^32-ms rollover. timeout_ms must be 1..INT32_MAX. */
int rc_init(rc_control *c, uint16_t expected_sender, uint32_t timeout_ms);
void rc_tick(rc_control *c, uint32_t now);
/* Returns 1 only for an accepted fresh valid command. Invalid/stale input
 * does not refresh either channel. Outputs remain safe while disarmed.
 * received_at is stamped when a complete frame is queued, not on dequeue. */
int rc_receive(rc_control *c, const char *line, size_t len,
               uint32_t received_at, uint32_t now);
/* Explicit trusted policy event; legacy THRUST/RUDDER NEVER arms.
 * Requires recent THRUST=0 AND RUDDER=50 since boot/disarm/recovery. */
int rc_arm(rc_control *c, uint32_t now);
void rc_disarm(rc_control *c);
void rc_trip(rc_control *c);
/* Explicit trusted recovery event after the fault cause is cleared. Only
 * returns to DISARMED; new neutral commands plus explicit arm are required. */
int rc_recover(rc_control *c);

#endif
