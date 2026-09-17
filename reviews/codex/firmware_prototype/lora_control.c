#include "lora_control.h"
#include <limits.h>
#include <string.h>

static int number(const char *s, size_t n, uint32_t max, uint32_t *out)
{
    size_t i;
    uint32_t v = 0;
    if (!n) return 0;
    for (i = 0; i < n; ++i) {
        uint32_t d;
        if (s[i] < '0' || s[i] > '9') return 0;
        d = (uint32_t)(s[i] - '0');
        if (d > max || v > (max - d) / 10u) return 0;
        v = v * 10u + d;
    }
    *out = v;
    return 1;
}

static int metadata_number(const char *s, size_t n)
{
    uint32_t ignored;
    uint32_t limit = 32767u;
    if (n && s[0] == '-') { ++s; --n; limit = 32768u; }
    return number(s, n, limit, &ignored);
}

static int field(const char *s, size_t len, size_t *at, uint32_t max,
                 uint32_t *value)
{
    size_t start = *at;
    while (*at < len && s[*at] != ',') ++*at;
    if (*at == len || !number(s + start, *at - start, max, value)) return 0;
    ++*at;
    return 1;
}

rc_parse_result rc_parse(const char *line, size_t len,
                         uint16_t expected_sender, rc_command *out)
{
    size_t at = 5u, payload_at, payload_end, rssi_at;
    uint32_t sender, declared, value;
    rc_command result;
    if (!line || !out || len > RC_MAX_LINE_BYTES) return RC_PARSE_FORMAT;
    if (len && line[len - 1u] == '\n') --len;
    if (len && line[len - 1u] == '\r') --len;
    if (len < 5u || memcmp(line, "+RCV=", 5u)) return RC_PARSE_FORMAT;
    if (!field(line, len, &at, 65535u, &sender)) return RC_PARSE_FORMAT;
    if (sender != expected_sender) return RC_PARSE_SENDER;
    if (!field(line, len, &at, RC_MAX_LINE_BYTES, &declared)) return RC_PARSE_LENGTH;
    payload_at = at;
    if (declared > len - at) return RC_PARSE_LENGTH;
    payload_end = at + (size_t)declared;
    if (payload_end == len || line[payload_end] != ',') return RC_PARSE_LENGTH;
    if (declared < 8u) return RC_PARSE_COMMAND;
    if (!memcmp(line + payload_at, "THRUST,", 7u)) result.kind = RC_THRUST;
    else if (!memcmp(line + payload_at, "RUDDER,", 7u)) result.kind = RC_RUDDER;
    else return RC_PARSE_COMMAND;
    if (!number(line + payload_at + 7u, declared - 7u, 100u, &value))
        return RC_PARSE_VALUE;
    result.value = (uint8_t)value;
    rssi_at = payload_end + 1u;
    at = rssi_at;
    while (at < len && line[at] != ',') ++at;
    if (at == len || !metadata_number(line + rssi_at, at - rssi_at))
        return RC_PARSE_FORMAT;
    ++at;
    if (!metadata_number(line + at, len - at)) return RC_PARSE_FORMAT;
    *out = result;
    return RC_PARSE_OK;
}

static void safe_output(rc_control *c)
{
    c->thrust = 0;
    c->rudder = 50;
}

static void clear_evidence(rc_control *c)
{
    c->seen[RC_THRUST] = 0;
    c->seen[RC_RUDDER] = 0;
    c->requested[RC_THRUST] = 0;
    c->requested[RC_RUDDER] = 50;
}

static void latch(rc_control *c, rc_fault fault)
{
    c->mode = RC_FAILSAFE;
    c->fault = fault;
    safe_output(c);
    clear_evidence(c);
}

int rc_init(rc_control *c, uint16_t expected_sender, uint32_t timeout_ms)
{
    if (!c) return 0;
    memset(c, 0, sizeof(*c));
    c->expected_sender = expected_sender;
    c->timeout_ms = timeout_ms;
    safe_output(c);
    clear_evidence(c);
    if (!timeout_ms || timeout_ms > INT32_MAX) {
        latch(c, RC_BAD_CONFIG);
        return 0;
    }
    c->mode = RC_DISARMED;
    return 1;
}

void rc_tick(rc_control *c, uint32_t now)
{
    unsigned i;
    if (!c || c->mode == RC_FAILSAFE) return;
    for (i = 0; i < 2u; ++i) {
        if (!c->seen[i] || (uint32_t)(now - c->received_at[i]) >= c->timeout_ms) {
            c->seen[i] = 0;
            if (c->mode == RC_ARMED) {
                latch(c, RC_LINK_EXPIRED);
                return;
            }
        }
    }
}

int rc_receive(rc_control *c, const char *line, size_t len,
               uint32_t received_at, uint32_t now)
{
    rc_command command;
    unsigned slot;
    if (!c) return 0;
    rc_tick(c, now); /* Never let a late command conceal an expired deadline. */
    if (c->mode == RC_FAILSAFE ||
        (uint32_t)(now - received_at) >= c->timeout_ms ||
        rc_parse(line, len, c->expected_sender, &command) != RC_PARSE_OK) return 0;
    slot = (unsigned)command.kind;
    if (c->seen[slot] && (uint32_t)(received_at - c->received_at[slot]) > INT32_MAX)
        return 0;
    c->received_at[slot] = received_at;
    c->seen[slot] = 1;
    c->requested[slot] = command.value;
    if (c->mode == RC_ARMED) {
        c->thrust = c->requested[RC_THRUST];
        c->rudder = c->requested[RC_RUDDER];
    }
    return 1;
}

int rc_arm(rc_control *c, uint32_t now)
{
    if (!c) return 0;
    rc_tick(c, now);
    if (c->mode != RC_DISARMED || !c->seen[RC_THRUST] || !c->seen[RC_RUDDER] ||
        c->requested[RC_THRUST] != 0 || c->requested[RC_RUDDER] != 50) return 0;
    c->mode = RC_ARMED;
    return 1;
}

void rc_disarm(rc_control *c)
{
    if (!c) return;
    safe_output(c);
    clear_evidence(c);
    if (c->mode != RC_FAILSAFE) c->mode = RC_DISARMED;
}

void rc_trip(rc_control *c)
{
    if (c && c->fault != RC_BAD_CONFIG) latch(c, RC_EXTERNAL_FAULT);
}

int rc_recover(rc_control *c)
{
    if (!c || c->mode != RC_FAILSAFE || c->fault == RC_BAD_CONFIG) return 0;
    c->mode = RC_DISARMED;
    c->fault = RC_NO_FAULT;
    safe_output(c);
    clear_evidence(c);
    return 1;
}
