/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body (Boat board – STM32F446RET: LoRa + GPS)
  ******************************************************************************
  * Peripherals (actual, based on testing):
  *   TIM1_CH1 (PA8)      -> Rudder servo PWM
  *   TIM3_CH1 (PC6)      -> Motor / Fans PWM
  *   PB0                 -> Debug LED / probe
  *
  *   UART4  (PA0 TX,  PA1 RX)   -> LoRa  @115200 (RYLR module)
  *   USART3(PC10 TX, PC11 RX)   -> GPS / DEBUG @9600
  *
  * Behavior:
  *   - PWM:
  *       Motor:  TIM3_CH1 / PC6, 50 Hz, 1000–2000 µs
  *       Rudder: TIM1_CH1 / PA8, 50 Hz, 1100–1900 µs (center ~1500)
  *
  *   - LoRa:
  *       AT startup:
  *         ATE0
  *         AT+ADDRESS=1        (BOAT)
  *         AT+NETWORKID=18
  *         AT+BAND=915000000
  *         AT+PARAMETER=12,7,1,4
  *
  *       Incoming lines (from +RCV=...):
  *         THRUST,<0–100>
  *         RUDDER,<0–100>   (0=left, 50=center, 100=right)
  *         GPS,<lat>,<lon>  (from other node, just printed)
  *
  *   - GPS:
  *       Parse $GPRMC / $GNRMC to gps_lat/gps_lon/gps_valid.
  *       Every 5s (if valid): send "GPS,<lat>,<lon>" via LoRa AT+SEND
  *       to RC node address 2.
  ******************************************************************************
  */
/* USER CODE END Header */

/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */
/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* GPS / LoRa line buffers */
#define GPS_BUF_LEN    128
#define LORA_BUF_LEN   128

/* LoRa addressing – must match RC firmware */
#define LORA_ADDR_RC    2   /* Remote: RC handset (L072) */
#define LORA_ADDR_BOAT  1   /* This boat node (F446) */
#define LORA_NET_ID    18
#define LORA_FREQ      915000000UL
#define LORA_PARAM_STR "12,7,1,4"

/* Motor PWM (PC6 – TIM3_CH1) */
#define PWM_MOTOR_MIN_US     1000U   /* ESC min / idle */
#define PWM_MOTOR_MAX_US     2000U
#define PWM_MOTOR_IDLE_US    PWM_MOTOR_MIN_US

/* Rudder PWM (PA8 – TIM1_CH1) */
#define PWM_RUDDER_CENTER_US 1500U
#define PWM_RUDDER_LEFT_US   1100U   /* tune if needed */
#define PWM_RUDDER_RIGHT_US  1900U

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */
/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
TIM_HandleTypeDef htim1;
TIM_HandleTypeDef htim3;

UART_HandleTypeDef huart4;   // LoRa
UART_HandleTypeDef huart3;   // GPS / debug

/* USER CODE BEGIN PV */

/* GPS RX state */
static uint8_t gps_rx_byte;
static char    gps_buf[GPS_BUF_LEN];
static volatile size_t gps_len   = 0;
static volatile uint8_t gps_ready = 0;

/* LoRa RX state */
static uint8_t lora_rx_byte;
static char    lora_buf[LORA_BUF_LEN];
static volatile size_t lora_len   = 0;
static volatile uint8_t lora_ready = 0;

/* Parsed GPS data */
float   gps_lat   = 0.0f;
float   gps_lon   = 0.0f;
uint8_t gps_valid = 0;

/* Last time we sent GPS over LoRa */
uint32_t last_lora_tx = 0;

/* Motor / rudder logical values */
uint8_t thrust_value = 0;   // 0..100 (0 = stop, 100 = full)
uint8_t rudder_value = 50;  // 0..100 (0=left, 50=center, 100=right)

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_UART4_Init(void);
static void MX_USART3_UART_Init(void);
static void MX_TIM1_Init(void);
static void MX_TIM3_Init(void);
/* USER CODE BEGIN PFP */
/* Debug helper */
static void dbg(const char *s);

/* High-level helpers */
static void set_thrust(uint8_t value);
static void set_rudder(uint8_t value);

/* UART IT helpers */
static void StartGPSRxIT(void);
static void StartLoRaRxIT(void);

/* LoRa helpers */
static void lora_send_line(const char* s);
static void lora_send_payload(const char* payload);
static void parse_lora_line(char* s);

/* GPS helpers */
static int  gps_ddmm_to_deg(const char* val, const char* hemi, float* out);
static int  gps_validate_checksum(const char* s);
static void gps_parse_rmc(char* line);
static void gps_task(void);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

static void dbg(const char *s)
{
  if (!s) return;
  /* Use finite timeout so a broken UART doesn't hard-lock */
  HAL_UART_Transmit(&huart3, (uint8_t*)s, strlen(s), 100);
}

/* Start interrupt receive for both UARTs */
static void StartGPSRxIT(void)
{
  HAL_UART_Receive_IT(&huart3, &gps_rx_byte, 1);
}

static void StartLoRaRxIT(void)
{
  HAL_UART_Receive_IT(&huart4, &lora_rx_byte, 1);
}

/* Simple AT line sender (adds \r\n) */
static void lora_send_line(const char* s)
{
  if (!s) return;

  /* Finite timeouts here too */
  HAL_UART_Transmit(&huart4, (uint8_t*)s, strlen(s), 100);
  uint8_t crlf[2] = { '\r', '\n' };
  HAL_UART_Transmit(&huart4, crlf, 2, 100);
}

/* AT+SEND payload helper:
 *  - Boat node address  = LORA_ADDR_BOAT (1)
 *  - RC handset address = LORA_ADDR_RC   (2)
 *  We send GPS/etc *to the RC*, so destination = LORA_ADDR_RC.
 */
static void lora_send_payload(const char* payload)
{
  if (!payload) return;
  char cmd[128];
  snprintf(cmd, sizeof(cmd),
           "AT+SEND=%d,%u,%s",
           LORA_ADDR_RC,           /* send TO RC (2) */
           (unsigned)strlen(payload),
           payload);
  lora_send_line(cmd);
}

/* Convert ddmm.mmmm -> decimal degrees */
static int gps_ddmm_to_deg(const char* val, const char* hemi, float* out)
{
  if (!val || !*val || !out) return 0;
  double v       = atof(val);
  int    deg     = (int)(v / 100);
  double minutes = v - (deg * 100.0);
  double result  = deg + minutes / 60.0;
  if (hemi && (*hemi == 'S' || *hemi == 'W')) result = -result;
  *out = (float)result;
  return 1;
}

/* Validate NMEA checksum */
static int gps_validate_checksum(const char* s)
{
  if (!s || s[0] != '$') return 0;
  const char* star = strrchr(s, '*');
  if (!star) return 0;

  uint8_t chk = 0;
  for (const char* p = s + 1; p < star; p++)
  {
    chk ^= (uint8_t)(*p);
  }
  uint8_t given = (uint8_t)strtol(star + 1, NULL, 16);
  return (chk == given);
}

/* Parse an RMC line (in-place strtok) */
static void gps_parse_rmc(char* line)
{
  if (!gps_validate_checksum(line)) return;

  char* toks[16];
  int   n = 0;

  for (char* tok = strtok(line, ","); tok && n < 16; tok = strtok(NULL, ","))
  {
    toks[n++] = tok;
  }
  if (n < 7) return;

  if (strncmp(toks[0], "$GPRMC", 6) != 0 &&
      strncmp(toks[0], "$GNRMC", 6) != 0)
  {
    return;
  }

  /* Status: A = active, V = void */
  if (toks[2][0] != 'A')
  {
    gps_valid = 0;
    return;
  }

  float lat, lon;
  if (!gps_ddmm_to_deg(toks[3], toks[4], &lat)) return;
  if (!gps_ddmm_to_deg(toks[5], toks[6], &lon)) return;

  gps_lat   = lat;
  gps_lon   = lon;
  gps_valid = 1;
}

/* GPS processing task (call from main loop) */
static void gps_task(void)
{
  if (!gps_ready) return;
  gps_ready = 0;

  char buf[GPS_BUF_LEN];
  strncpy(buf, gps_buf, sizeof(buf));
  buf[GPS_BUF_LEN - 1] = '\0';

  if (strncmp(buf, "$GPRMC", 6) == 0 || strncmp(buf, "$GNRMC", 6) == 0)
  {
    gps_parse_rmc(buf);
  }
}

/* Parse one LoRa line from RYLR ("+RCV=...") */
static void parse_lora_line(char* s)
{
  if (!s) return;

  /* Skip leading CR/LF/spaces so "\r+RCV=..." still matches */
  while (*s == '\r' || *s == '\n' || *s == ' ' || *s == '\t')
  {
    s++;
  }

  if (*s == '\0') return;

  /* Expect lines like:
   *   +RCV=1,10,THRUST,50,-50,12
   *   +RCV=1,10,RUDDER,30,-70,11
   */
  if (strncmp(s, "+RCV=", 5) != 0 && strncmp(s, "RCV=", 4) != 0)
  {
    return;
  }

  /* Skip header up to second comma, then data starts */
  char* p = s;
  int   comma_count = 0;
  while (*p && comma_count < 2)
  {
    if (*p == ',') comma_count++;
    p++;
  }
  if (comma_count < 2) return;  // malformed
  char* data = p;               // points at payload: "THRUST,50,..."

  /* Normalize: strip trailing \r or \n */
  char* end = data + strlen(data);
  while (end > data && (end[-1] == '\r' || end[-1] == '\n'))
  {
    *--end = '\0';
  }

  /* Commands:
   *  THRUST,<0-100>
   *  RUDDER,<0-100>
   *  GPS,<lat>,<lon>
   */

  if (strncmp(data, "THRUST,", 7) == 0)
  {
    int value;
    if (sscanf(data, "THRUST,%d", &value) == 1)
    {
      if (value < 0)   value = 0;
      if (value > 100) value = 100;
      thrust_value = (uint8_t)value;
      set_thrust(thrust_value);

      char dbg_buf[64];
      snprintf(dbg_buf, sizeof(dbg_buf), "LoRa: THRUST=%d\r\n", value);
      dbg(dbg_buf);
    }
  }
  else if (strncmp(data, "RUDDER,", 7) == 0)
  {
    int value;
    if (sscanf(data, "RUDDER,%d", &value) == 1)
    {
      if (value < 0)   value = 0;
      if (value > 100) value = 100;
      rudder_value = (uint8_t)value;
      set_rudder(rudder_value);

      char dbg_buf[64];
      snprintf(dbg_buf, sizeof(dbg_buf), "LoRa: RUDDER=%d\r\n", value);
      dbg(dbg_buf);
    }
  }
  else if (strncmp(data, "GPS,", 4) == 0)
  {
    float lat, lon;
    if (sscanf(data, "GPS,%f,%f", &lat, &lon) == 2)
    {
      char dbg_buf[80];
      snprintf(dbg_buf, sizeof(dbg_buf),
               "LoRa: GPS from RC: %.6f, %.6f\r\n", lat, lon);
      dbg(dbg_buf);
    }
  }
}

/* Set motor thrust (0..100) → TIM3_CH1 / PC6 */
static void set_thrust(uint8_t value)
{
  if (value > 100) value = 100;

  uint32_t range = (PWM_MOTOR_MAX_US - PWM_MOTOR_MIN_US); // 1000
  uint32_t pulse = PWM_MOTOR_MIN_US + (range * value) / 100U;

  __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, pulse);
  thrust_value = value;
}

/* Set rudder (0..100) → TIM1_CH1 / PA8
 * 0   = fully left  (PWM_RUDDER_LEFT_US)
 * 50  = center      (PWM_RUDDER_CENTER_US)
 * 100 = fully right (PWM_RUDDER_RIGHT_US)
 */
static void set_rudder(uint8_t value)
{
  if (value > 100) value = 100;

  uint32_t range = (PWM_RUDDER_RIGHT_US - PWM_RUDDER_LEFT_US);
  uint32_t pulse = PWM_RUDDER_LEFT_US + (range * value) / 100U;

  __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, pulse);
  rudder_value = value;
}

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */

int main(void)
{
  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();   // sets up uwTick, SysTick, HAL_Delay, etc.

  /* Configure the system clock */
  SystemClock_Config();

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_UART4_Init();
  MX_USART3_UART_Init();
  MX_TIM1_Init();
  MX_TIM3_Init();

  /* NVIC setup for UART interrupts (must match stm32f4xx_it.c IRQHandlers) */
  HAL_NVIC_SetPriority(UART4_IRQn, 5, 0);
  HAL_NVIC_EnableIRQ(UART4_IRQn);

  HAL_NVIC_SetPriority(USART3_IRQn, 5, 0);
  HAL_NVIC_EnableIRQ(USART3_IRQn);

  /* Start PWM on both channels */
  if (HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1) != HAL_OK) { Error_Handler(); }
  if (HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1) != HAL_OK) { Error_Handler(); }

  /* Safe startup: motor idle, rudder centered */
  set_thrust(0);
  set_rudder(50);

  /* Let ESC/servo/LoRa/GPS power up */
  HAL_Delay(1500);

  /* Start UART reception in interrupt mode */
  StartGPSRxIT();
  StartLoRaRxIT();

  /* Configure LoRa module via AT commands */
  lora_send_line("ATE0");                        // Echo off
  lora_send_line("AT+ADDRESS=1");                // This node address (boat)
  lora_send_line("AT+NETWORKID=18");             // Network ID
  lora_send_line("AT+BAND=915000000");           // 915 MHz
  lora_send_line("AT+PARAMETER=" LORA_PARAM_STR);// SF12,BW7.8,CR4/5,PL=4

  dbg("Boat: LoRa init done\r\n");

  /* Infinite loop */
  while (1)
  {
    /* Handle GPS parsing */
    gps_task();

    /* Process any complete LoRa line */
    if (lora_ready)
    {
      lora_ready = 0;
      char buf_local[LORA_BUF_LEN];
      strncpy(buf_local, lora_buf, sizeof(buf_local));
      buf_local[LORA_BUF_LEN - 1] = '\0';

      dbg("LORA RX: ");
      dbg(buf_local);
      dbg("\r\n");

      parse_lora_line(buf_local);
    }

    uint32_t now = HAL_GetTick();

    /* Send *our* GPS over LoRa every 5 seconds if valid */
    if (gps_valid && (now - last_lora_tx >= 5000U))
    {
      char payload[64];
      snprintf(payload, sizeof(payload), "GPS,%.6f,%.6f", gps_lat, gps_lon);
      lora_send_payload(payload);
      last_lora_tx = now;
    }

    HAL_Delay(10);
  }
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Configure the main internal regulator output voltage */
  __HAL_RCC_PWR_CLK_ENABLE();
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE3);

  /** Initializes the RCC Oscillators according to the specified parameters */
  RCC_OscInitStruct.OscillatorType      = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState            = RCC_HSI_ON;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  RCC_OscInitStruct.PLL.PLLState        = RCC_PLL_NONE;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks */
  RCC_ClkInitStruct.ClockType      = RCC_CLOCKTYPE_HCLK
                                   | RCC_CLOCKTYPE_SYSCLK
                                   | RCC_CLOCKTYPE_PCLK1
                                   | RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource   = RCC_SYSCLKSOURCE_HSI;
  RCC_ClkInitStruct.AHBCLKDivider  = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_0) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief TIM1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM1_Init(void)
{
  TIM_MasterConfigTypeDef sMasterConfig = {0};
  TIM_OC_InitTypeDef      sConfigOC     = {0};
  TIM_BreakDeadTimeConfigTypeDef sBreakDeadTimeConfig = {0};

  htim1.Instance               = TIM1;
  htim1.Init.Prescaler         = 15;
  htim1.Init.CounterMode       = TIM_COUNTERMODE_UP;
  htim1.Init.Period            = 19999;
  htim1.Init.ClockDivision     = TIM_CLOCKDIVISION_DIV1;
  htim1.Init.RepetitionCounter = 0;
  htim1.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
  if (HAL_TIM_PWM_Init(&htim1) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode     = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim1, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sConfigOC.OCMode       = TIM_OCMODE_PWM1;
  sConfigOC.Pulse        = PWM_RUDDER_CENTER_US;
  sConfigOC.OCPolarity   = TIM_OCPOLARITY_HIGH;
  sConfigOC.OCNPolarity  = TIM_OCNPOLARITY_HIGH;
  sConfigOC.OCFastMode   = TIM_OCFAST_DISABLE;
  sConfigOC.OCIdleState  = TIM_OCIDLESTATE_RESET;
  sConfigOC.OCNIdleState = TIM_OCNIDLESTATE_RESET;
  if (HAL_TIM_PWM_ConfigChannel(&htim1, &sConfigOC, TIM_CHANNEL_1) != HAL_OK)
  {
    Error_Handler();
  }
  sBreakDeadTimeConfig.OffStateRunMode  = TIM_OSSR_DISABLE;
  sBreakDeadTimeConfig.OffStateIDLEMode = TIM_OSSI_DISABLE;
  sBreakDeadTimeConfig.LockLevel        = TIM_LOCKLEVEL_OFF;
  sBreakDeadTimeConfig.DeadTime         = 0;
  sBreakDeadTimeConfig.BreakState       = TIM_BREAK_DISABLE;
  sBreakDeadTimeConfig.BreakPolarity    = TIM_BREAKPOLARITY_HIGH;
  sBreakDeadTimeConfig.AutomaticOutput  = TIM_AUTOMATICOUTPUT_DISABLE;
  if (HAL_TIMEx_ConfigBreakDeadTime(&htim1, &sBreakDeadTimeConfig) != HAL_OK)
  {
    Error_Handler();
  }
  HAL_TIM_MspPostInit(&htim1);
}

/**
  * @brief TIM3 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM3_Init(void)
{
  TIM_MasterConfigTypeDef sMasterConfig = {0};
  TIM_OC_InitTypeDef      sConfigOC     = {0};

  htim3.Instance               = TIM3;
  htim3.Init.Prescaler         = 15;
  htim3.Init.CounterMode       = TIM_COUNTERMODE_UP;
  htim3.Init.Period            = 19999;
  htim3.Init.ClockDivision     = TIM_CLOCKDIVISION_DIV1;
  htim3.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
  if (HAL_TIM_PWM_Init(&htim3) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode     = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim3, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sConfigOC.OCMode     = TIM_OCMODE_PWM1;
  sConfigOC.Pulse      = PWM_MOTOR_IDLE_US;
  sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
  sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
  if (HAL_TIM_PWM_ConfigChannel(&htim3, &sConfigOC, TIM_CHANNEL_1) != HAL_OK)
  {
    Error_Handler();
  }
  HAL_TIM_MspPostInit(&htim3);
}

/**
  * @brief UART4 Initialization Function
  * @param None
  * @retval None
  */
static void MX_UART4_Init(void)
{
  huart4.Instance        = UART4;
  huart4.Init.BaudRate   = 115200;
  huart4.Init.WordLength = UART_WORDLENGTH_8B;
  huart4.Init.StopBits   = UART_STOPBITS_1;
  huart4.Init.Parity     = UART_PARITY_NONE;
  huart4.Init.Mode       = UART_MODE_TX_RX;
  huart4.Init.HwFlowCtl  = UART_HWCONTROL_NONE;
  huart4.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart4) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief USART3 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART3_UART_Init(void)
{
  huart3.Instance        = USART3;
  huart3.Init.BaudRate   = 9600;
  huart3.Init.WordLength = UART_WORDLENGTH_8B;
  huart3.Init.StopBits   = UART_STOPBITS_1;
  huart3.Init.Parity     = UART_PARITY_NONE;
  huart3.Init.Mode       = UART_MODE_TX_RX;
  huart3.Init.HwFlowCtl  = UART_HWCONTROL_NONE;
  huart3.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart3) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_RESET);

  /*Configure GPIO pin : PB0 (debug LED / probe) */
  GPIO_InitStruct.Pin   = GPIO_PIN_0;
  GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull  = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);
}

/* USER CODE BEGIN 4 */

/* UART receive complete callback (called from IRQs via HAL_UART_IRQHandler) */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
  if (huart->Instance == USART3)  /* GPS */
  {
    char c = (char)gps_rx_byte;

    if (c == '\n')
    {
      gps_buf[gps_len] = '\0';
      gps_ready = 1;
      gps_len = 0;
    }
    else
    {
      if (gps_len < (GPS_BUF_LEN - 1))
      {
        gps_buf[gps_len++] = c;
      }
    }
    StartGPSRxIT();
  }
  else if (huart->Instance == UART4)  /* LoRa */
  {
    char c = (char)lora_rx_byte;

    if (c == '\n')
    {
      lora_buf[lora_len] = '\0';
      lora_ready = 1;
      lora_len = 0;
    }
    else
    {
      if (lora_len < (LORA_BUF_LEN - 1))
      {
        lora_buf[lora_len++] = c;
      }
    }
    StartLoRaRxIT();
  }
}

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  __disable_irq();
  while (1)
  {
  }
}

#ifdef USE_FULL_ASSERT
void assert_failed(uint8_t *file, uint32_t line)
{
  (void)file;
  (void)line;
}
#endif /* USE_FULL_ASSERT */
