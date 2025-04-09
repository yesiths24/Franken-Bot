#include "lcd_1602_i2c.cpp"

void franken_eyes_straight() {
    lcd_clear();
    lcd_set_cursor(0,3);
    lcd_char((char) 255);
    lcd_char((char) 255);
    lcd_char((char) 255);

    lcd_set_cursor(0, 14);
    lcd_char((char) 255);
    lcd_char((char) 255);
    lcd_char((char) 255);

    lcd_set_cursor(1,4);
    lcd_char((char) 255);
    lcd_char((char) 255);

    lcd_set_cursor(1,14);
    lcd_char((char) 255);
    lcd_char((char) 255);


}

void franken_eyes_left() {
    lcd_clear();
    lcd_set_cursor(0,0);
    lcd_char((char) 255);
    lcd_char((char) 255);
    lcd_char((char) 255);

    lcd_set_cursor(0, 11);
    lcd_char((char) 255);
    lcd_char((char) 255);
    lcd_char((char) 255);

    lcd_set_cursor(1,1);
    lcd_char((char) 255);
    lcd_char((char) 255);

    lcd_set_cursor(1,11);
    lcd_char((char) 255);
    lcd_char((char) 255);


}

void franken_eyes_right() {
    lcd_clear();
    lcd_set_cursor(0,6);
    lcd_char((char) 255);
    lcd_char((char) 255);
    lcd_char((char) 255);

    lcd_set_cursor(0, 17);
    lcd_char((char) 255);
    lcd_char((char) 255);
    lcd_char((char) 255);

    lcd_set_cursor(1,7);
    lcd_char((char) 255);
    lcd_char((char) 255);

    lcd_set_cursor(1,17);
    lcd_char((char) 255);
    lcd_char((char) 255);


}