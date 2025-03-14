#include "pico/stdlib.h"
#include "hardware/pwm.h"
#include "hardware/clocks.h"
#include "math.h"

#define PIN_STBY 2
#define PIN_A1 4
#define PIN_A2 5
#define PIN_B1 7
#define PIN_B2 8
#define PIN_PWMA 3
#define PIN_PWMB 6

#define PWM_MAX 14000
#define PWM_MIN 0


void initDrive() {

    gpio_init(PIN_STBY);
    gpio_init(PIN_A1);
    gpio_init(PIN_A2);
    gpio_init(PIN_B1);
    gpio_init(PIN_B2);
    gpio_init(PIN_PWMA);
    gpio_init(PIN_PWMB);

    gpio_set_dir(PIN_STBY, GPIO_OUT);
    gpio_set_dir(PIN_A1, GPIO_OUT);
    gpio_set_dir(PIN_A2, GPIO_OUT);
    gpio_set_dir(PIN_B1, GPIO_OUT);
    gpio_set_dir(PIN_B2, GPIO_OUT);
    gpio_set_dir(PIN_PWMA, GPIO_OUT);
    gpio_set_dir(PIN_PWMB, GPIO_OUT);

    pwm_config config = pwm_get_default_config();
    float div = (float) clock_get_hz(clk_sys) / (980 * 100000);
    pwm_config_set_clkdiv(&config, div);
    pwm_config_set_wrap(&config, 10000);

    gpio_set_function(PIN_PWMA, GPIO_FUNC_PWM);
    uint slice_num = pwm_gpio_to_slice_num(PIN_PWMA);
    pwm_init(slice_num, &config, true);
    pwm_set_gpio_level(PIN_PWMA, 0);

    gpio_set_function(PIN_PWMB, GPIO_FUNC_PWM);
    slice_num = pwm_gpio_to_slice_num(PIN_PWMB);
    pwm_init(slice_num, &config, true);
    pwm_set_gpio_level(PIN_PWMB, 0);

    gpio_put(PIN_A1, 0);
    gpio_put(PIN_A2, 1);
    gpio_put(PIN_B1, 0);
    gpio_put(PIN_B2, 1);
    gpio_put(PIN_STBY, 1);


}

void setMotorSpeed(int motor, float speed) {
    printf("Setting motor %d to speed %f\n", motor, speed);
    short unsigned int pwmLevelA, pwmLevelB;
    float speedFrac;
    switch(motor) {
        case 0:
            if (speed >= 0) {
                gpio_put(PIN_A1, 0);
                gpio_put(PIN_A2, 1);
                pwmLevelA = (speed / 100 * PWM_MAX);

            } else {
                gpio_put(PIN_A1, 1);
                gpio_put(PIN_A2, 0);
                pwmLevelA = -1 * (speed / 100 * PWM_MAX);
            }
            // speedFrac = abs(speed) / 100;

            // short unsigned int pwmLevelA = (short unsigned int) (speedFrac * (float) ((PWM_MAX - PWM_MIN) + PWM_MIN)); 
            printf("Setting PWM %d to level %d\n", motor, pwmLevelA);
            pwm_set_gpio_level(PIN_PWMA, pwmLevelA);

            break;
        case 1:
            if (speed >= 0) {
                gpio_put(PIN_B1, 0);
                gpio_put(PIN_B2, 1);
                pwmLevelB = (speed / 100 * PWM_MAX);
            } else {
                gpio_put(PIN_B1, 1);
                gpio_put(PIN_B2, 0);
                pwmLevelB = (-1 * speed / 100 * PWM_MAX);
            }
            // speedFrac = abs(speed) / 100;
            // short unsigned int pwmLevelB = (short unsigned int) (speedFrac * (float) ((PWM_MAX - PWM_MIN) + PWM_MIN));
            printf("Setting PWM %d to level %d\n", motor, pwmLevelB);
            pwm_set_gpio_level(PIN_PWMB, pwmLevelB);
            break;
    }
}

void setDriveSpeeds(float left, float right) {
    printf("setting drives to %f, %f\n", left, right);
    setMotorSpeed(0, left);
    setMotorSpeed(1, right);
}