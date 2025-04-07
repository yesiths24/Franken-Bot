#include "pico/stdlib.h"
#include "hardware/pwm.h"
#include "hardware/clocks.h"
#include "math.h"
#include "hwconfigs.h"


void init_drive() {

    gpio_init(DRV_PIN_STBY);
    gpio_init(DRV_PIN_A1);
    gpio_init(DRV_PIN_A2);
    gpio_init(DRV_PIN_B1);
    gpio_init(DRV_PIN_B2);
    gpio_init(DRV_PIN_PWMA);
    gpio_init(DRV_PIN_PWMB);

    gpio_set_dir(DRV_PIN_STBY, GPIO_OUT);
    gpio_set_dir(DRV_PIN_A1, GPIO_OUT);
    gpio_set_dir(DRV_PIN_A2, GPIO_OUT);
    gpio_set_dir(DRV_PIN_B1, GPIO_OUT);
    gpio_set_dir(DRV_PIN_B2, GPIO_OUT);
    gpio_set_dir(DRV_PIN_PWMA, GPIO_OUT);
    gpio_set_dir(DRV_PIN_PWMB, GPIO_OUT);

    pwm_config config = pwm_get_default_config();
    float div = (float) clock_get_hz(clk_sys) / (980 * 100000);
    pwm_config_set_clkdiv(&config, div);
    pwm_config_set_wrap(&config, 10000);

    gpio_set_function(DRV_PIN_PWMA, GPIO_FUNC_PWM);
    uint slice_num = pwm_gpio_to_slice_num(DRV_PIN_PWMA);
    pwm_init(slice_num, &config, true);
    pwm_set_gpio_level(DRV_PIN_PWMA, 0);

    gpio_set_function(DRV_PIN_PWMB, GPIO_FUNC_PWM);
    slice_num = pwm_gpio_to_slice_num(DRV_PIN_PWMB);
    pwm_init(slice_num, &config, true);
    pwm_set_gpio_level(DRV_PIN_PWMB, 0);

    gpio_put(DRV_PIN_A1, 0);
    gpio_put(DRV_PIN_A2, 1);
    gpio_put(DRV_PIN_B1, 0);
    gpio_put(DRV_PIN_B2, 1);
    gpio_put(DRV_PIN_STBY, 1);


}

void set_motor_speed(int motor, float speed) {
    short unsigned int pwmLevelA, pwmLevelB;
    float speedFrac;
    switch(motor) {
        case 0:
            if (speed >= 0) {
                gpio_put(DRV_PIN_A1, 0);
                gpio_put(DRV_PIN_A2, 1);
                pwmLevelA = (speed / 100 * (DRV_PWMA_MAX-DRV_PWMA_MIN)) + DRV_PWMA_MIN;

            } else {
                gpio_put(DRV_PIN_A1, 1);
                gpio_put(DRV_PIN_A2, 0);
                pwmLevelA = -1 * ((speed / 100 * (DRV_PWMA_MAX-DRV_PWMA_MIN)) + DRV_PWMA_MIN);
            }

            pwm_set_gpio_level(DRV_PIN_PWMA, pwmLevelA);

            break;
        case 1:
            if (speed >= 0) {
                gpio_put(DRV_PIN_B1, 0);
                gpio_put(DRV_PIN_B2, 1);
                pwmLevelB = (speed / 100 * (DRV_PWMB_MAX - DRV_PWMB_MIN)) + DRV_PWMB_MIN;
            } else {
                gpio_put(DRV_PIN_B1, 1);
                gpio_put(DRV_PIN_B2, 0);
                pwmLevelB = -1 * ((speed / 100 * (DRV_PWMB_MAX - DRV_PWMB_MIN)) + DRV_PWMB_MIN);
            }

            pwm_set_gpio_level(DRV_PIN_PWMB, pwmLevelB);
            break;
    }
}

void set_drive_speeds(float left, float right) {
    set_motor_speed(0, left);
    set_motor_speed(1, right);
}