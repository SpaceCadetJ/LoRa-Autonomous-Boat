/* Stage A development diagnostic. No radio commands or actuator pulses.
 * Start only after hardware power review; use with actuator loads disconnected.
 * CMSIS register definitions come from the preserved ST vendor package. */
#include "stm32f4xx.h"
#include "board_pins.h"

typedef struct {
    uint32_t magic;
    uint32_t version;
    uint32_t stage;
    uint32_t reset_flags;
    uint32_t device_id;
    uint32_t core_clock_hz;
    uint32_t milliseconds;
    uint32_t heartbeat_edges;
} diagnostic_record;

/* Inspect this symbol through SWD with the matching ELF loaded. */
volatile diagnostic_record v2_diagnostic;

static void output_low(GPIO_TypeDef *port, uint32_t pin)
{
    /* Set the latch before enabling the driver; preserve all other pins. */
    port->BSRR = 1u << (pin + 16u);
    port->OTYPER &= ~(1u << pin);
    port->OSPEEDR &= ~(3u << (pin * 2u));
    port->PUPDR &= ~(3u << (pin * 2u));
    port->MODER = (port->MODER & ~(3u << (pin * 2u))) | (1u << (pin * 2u));
}

static void hold_actuators_low(void)
{
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOCEN;
    (void)RCC->AHB1ENR;
    output_low(ESC_PORT, ESC_PIN);
    output_low(SERVO_PORT, SERVO_PIN);
}

static void stop_diagnostic(uint32_t reason)
{
    __disable_irq();
    hold_actuators_low();
    v2_diagnostic.stage = reason;
    for (;;) { __WFI(); }
}

void HardFault_Handler(void) { stop_diagnostic(0xF1u); }
void MemManage_Handler(void) { stop_diagnostic(0xF2u); }
void BusFault_Handler(void) { stop_diagnostic(0xF3u); }
void UsageFault_Handler(void) { stop_diagnostic(0xF4u); }
void NMI_Handler(void) { stop_diagnostic(0xF5u); }

void SysTick_Handler(void)
{
    ++v2_diagnostic.milliseconds;
    if (v2_diagnostic.milliseconds % 500u == 0u) {
        ++v2_diagnostic.heartbeat_edges;
        HEARTBEAT_PORT->BSRR = (v2_diagnostic.heartbeat_edges & 1u)
            ? (1u << HEARTBEAT_PIN) : (1u << (HEARTBEAT_PIN + 16u));
    }
}

int main(void)
{
    hold_actuators_low();
    output_low(HEARTBEAT_PORT, HEARTBEAT_PIN);
    output_low(FIX_PORT, FIX_PIN);
    output_low(MARKER_PORT, MARKER_PIN);
    MARKER_PORT->BSRR = 1u << MARKER_PIN; /* On means diagnostic edition. */
    v2_diagnostic.magic = 0x3252564Cu;
    v2_diagnostic.version = 1u;
    v2_diagnostic.stage = 1u;
    v2_diagnostic.reset_flags = RCC->CSR;
    v2_diagnostic.device_id = DBGMCU->IDCODE;
    SystemCoreClockUpdate();
    v2_diagnostic.core_clock_hz = SystemCoreClock;
    /* A true reset starts on HSI. Reject a debugger handoff with other clocks. */
    if (SystemCoreClock != 16000000u || (RCC->CFGR & RCC_CFGR_SWS) != 0u)
        stop_diagnostic(0xE1u);
    if (SysTick_Config(SystemCoreClock / 1000u) != 0u)
        stop_diagnostic(0xE2u);
    v2_diagnostic.stage = 2u;
    for (;;) { __WFI(); }
}
