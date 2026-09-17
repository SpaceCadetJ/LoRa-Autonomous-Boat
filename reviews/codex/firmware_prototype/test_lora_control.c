#include "lora_control.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

#define T0 "+RCV=2,8,THRUST,0,-70,12"
#define T50 "+RCV=2,9,THRUST,50,-70,12"
#define R50 "+RCV=2,9,RUDDER,50,-70,12"
#define R80 "+RCV=2,9,RUDDER,80,-70,12"
#define RECEIVE(c, s, rx, now) rc_receive(c, s, sizeof(s)-1u, rx, now)

static void parser_tests(void)
{
    static const char *invalid[] = {
        "RCV=2,8,THRUST,0,-70,12", " +RCV=2,8,THRUST,0,-70,12",
        "+RCV=1,8,THRUST,0,-70,12", "+RCV=2,7,THRUST,0,-70,12",
        "+RCV=2,9,THRUST,0,-70,12", "+RCV=2,99999999999,THRUST,0,-70,12",
        "+RCV=2,9,THRUST,-1,-70,12", "+RCV=2,10,THRUST,101,-70,12",
        "+RCV=2,9,THRUST,0x,-70,12", "+RCV=2,9,THRUST,+1,-70,12",
        "+RCV=2,9,THRUST, 1,-70,12", "+RCV=2,9,THRUST,50,-70,12junk",
        "+RCV=2,9,THRUST,50,-70,12,0", "+RCV=2,9,THRUST,50,-70",
        "+RCV=2,9,THRUST,50,,-1", "+RCV=2,9,THRUST,50,-,12",
        "+RCV=2,9,THRUST,50,-32769,12", "+RCV=2,9,THRUST,50,-70,32768",
        "+RCV=2,9,THRUST,50,-70,12\n\n", "+RCV=2,9,thrust,50,-70,12",
        "+RCV=2,7,THRUST,,-70,12", "+RCV=2,8,ARM,0000,-70,12",
        "+RCV=65536,8,THRUST,0,-70,12", "+RCV=2,-1,THRUST,0,-70,12"
    };
    rc_command out = { RC_RUDDER, 42 };
    size_t i;
    assert(rc_parse(T0, sizeof(T0)-1u, 2, &out) == RC_PARSE_OK);
    assert(out.kind == RC_THRUST && out.value == 0);
    assert(rc_parse("+RCV=2,10,THRUST,100,-70,-5\r\n", 29u, 2, &out) == RC_PARSE_OK);
    assert(out.value == 100);
    assert(rc_parse(R50 "\r", sizeof(R50 "\r")-1u, 2, &out) == RC_PARSE_OK);
    assert(out.kind == RC_RUDDER && out.value == 50);
    assert(rc_parse(R50 "\n", sizeof(R50 "\n")-1u, 2, &out) == RC_PARSE_OK);
    for (i = 0; i < sizeof(invalid)/sizeof(invalid[0]); ++i) {
        out.kind = RC_RUDDER; out.value = 42;
        assert(rc_parse(invalid[i], strlen(invalid[i]), 2, &out) != RC_PARSE_OK);
        assert(out.kind == RC_RUDDER && out.value == 42);
    }
    for (i = 0; i < sizeof(T50)-2u; ++i)
        assert(rc_parse(T50, i, 2, &out) != RC_PARSE_OK);
    /* An embedded NUL is a byte, never an implicit early end. */
    {
        char embedded[] = T50;
        embedded[17] = '\0';
        assert(rc_parse(embedded, sizeof(embedded)-1u, 2, &out) != RC_PARSE_OK);
    }
    assert(rc_parse(NULL, 0, 2, &out) != RC_PARSE_OK);
    assert(rc_parse(T0, sizeof(T0)-1u, 2, NULL) != RC_PARSE_OK);
    assert(rc_parse(T0, RC_MAX_LINE_BYTES+1u, 2, &out) != RC_PARSE_OK);
}

static void neutral_and_arm(rc_control *c, uint32_t t)
{
    assert(RECEIVE(c, T0, t, t));
    assert(RECEIVE(c, R50, t, t));
    assert(rc_arm(c, t));
}

static void state_tests(void)
{
    rc_control c;
    /* 100 ms is a synthetic test parameter, not a deployment requirement. */
    assert(rc_init(&c, 2, 100));
    assert(c.mode == RC_DISARMED && c.thrust == 0 && c.rudder == 50);
    assert(!rc_arm(&c, 0));
    assert(RECEIVE(&c, T50, 0, 0));
    assert(RECEIVE(&c, R50, 0, 0));
    assert(c.thrust == 0 && !rc_arm(&c, 0));
    neutral_and_arm(&c, 1);
    assert(RECEIVE(&c, T50, 2, 2) && c.thrust == 50);
    assert(RECEIVE(&c, R80, 90, 90) && c.rudder == 80);
    rc_tick(&c, 101);
    assert(c.mode == RC_ARMED);
    rc_tick(&c, 102); /* Rudder traffic cannot renew the thrust deadline. */
    assert(c.mode == RC_FAILSAFE && c.fault == RC_LINK_EXPIRED);
    assert(c.thrust == 0 && c.rudder == 50);
    assert(!RECEIVE(&c, T0, 103, 103) && !rc_arm(&c, 103));
    rc_disarm(&c);
    assert(c.mode == RC_FAILSAFE); /* disarm never clears a latched fault */
    assert(rc_recover(&c) && c.mode == RC_DISARMED && !rc_arm(&c, 104));
    neutral_and_arm(&c, 104);
    rc_trip(&c);
    assert(c.mode == RC_FAILSAFE && c.fault == RC_EXTERNAL_FAULT);
    assert(c.thrust == 0 && c.rudder == 50);
    assert(rc_recover(&c));

    neutral_and_arm(&c, 200);
    assert(!RECEIVE(&c, T50, 300, 300)); /* late valid packet cannot resurrect */
    assert(c.mode == RC_FAILSAFE);
    assert(rc_recover(&c));
    assert(!RECEIVE(&c, T50, 200, 301)); /* stale queued frame */
    assert(!RECEIVE(&c, T50, 302, 301)); /* future timestamp */
    assert(RECEIVE(&c, T0, 310, 310));
    assert(!RECEIVE(&c, T50, 309, 311)); /* out-of-order local queue */
    assert(RECEIVE(&c, R50, 310, 311));
    assert(rc_arm(&c, 311));
    assert(!RECEIVE(&c, "+RCV=3,9,THRUST,50,-70,12", 320, 320));
    rc_tick(&c, 410);
    assert(c.mode == RC_FAILSAFE); /* wrong sender did not extend freshness */

    assert(rc_init(&c, 2, 100));
    neutral_and_arm(&c, UINT32_MAX-49u);
    rc_tick(&c, 49u);
    assert(c.mode == RC_ARMED);
    rc_tick(&c, 50u);
    assert(c.mode == RC_FAILSAFE); /* unsigned clock rollover */
    assert(rc_init(&c, 2, 100));
    neutral_and_arm(&c, 0);
    assert(RECEIVE(&c, T50, 90, 90));
    rc_tick(&c, 100);
    assert(c.mode == RC_FAILSAFE); /* throttle traffic cannot mask rudder loss */
    assert(rc_init(&c, 2, 100));
    assert(RECEIVE(&c, T0, 0, 0));
    assert(RECEIVE(&c, R50, 0, 0));
    assert(!rc_arm(&c, 100)); /* neutral evidence expires while disarmed */
    neutral_and_arm(&c, 101);
    rc_disarm(&c);
    assert(c.mode == RC_DISARMED && !rc_arm(&c, 101));
    assert(!rc_init(&c, 2, 0) && c.fault == RC_BAD_CONFIG);
    assert(!rc_recover(&c));
    assert(!rc_init(&c, 2, UINT32_MAX));
    assert(!rc_init(NULL, 2, 100));
}

int main(void)
{
    parser_tests();
    state_tests();
    puts("PASS: strict parser and control-state test groups");
    return 0;
}
