/*
The MIT License (MIT)

Copyright (c) [2015] [Giovanni Bonomini]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/
#define F_OSC 16000000UL
#define BAUDRATE 1000000
#define BAUD_PRESCALLER (((F_OSC/16) + (BAUDRATE/2))/BAUDRATE) - 1

/* option definition */
#define TRIGGER_ON  0x80
#define TRIGGER_OFF 0x00
#define RISING_EDGE 0x10
#define FALLING_EDGE 0x20
#define F_1M  0x01
#define F_500k  0x02
#define F_250k  0x03
#define F_125k  0x04

/* command definition */
#define START_CMD 0xAA
#define ACK_CMD 0xCC
#define DATA_CMD 0xEE

/* state definition */
#define ADC_START 2
#define ADC_CONV 3
#define WAIT_DATA 4
#define SEND_DATA 5
#define GET_CMD 6 
#define GET_2_BYTE 7

/* dimension definition */
#define COMMAND_SIZE 5
#define BUFFER_SIZE 8000

/* ADC channel definition */
#define CH 0x01

/* global variables definition */
volatile uint8_t command[COMMAND_SIZE];
volatile uint8_t uart_buffer_ptr;
volatile uint16_t acquisition_buffer_ptr;
volatile uint8_t end_flag; 
volatile uint8_t acquisition_buffer[BUFFER_SIZE];
volatile uint8_t last_sample;
volatile uint8_t start_sample_pos_l;
volatile uint8_t start_sample_pos_h;
volatile uint16_t count_sample;
uint8_t state;


void setup_uart()
{
  //asynchronous mode
  UCSR0C &= 0x3F;
  //parity none
  UCSR0C &= 0xCF;
  //stop bit 1
  UCSR0C &= 0xF7;
  //character size 8
  UCSR0C |= 0x03;
  //clock polarity
  UCSR0C &= 0xFE;
  //set baud rate
  UBRR0H = 0;
  //(BAUD_PRESCALLER>>8);
  UBRR0L = 0;
  //(BAUD_PRESCALLER);
  //enable the UART TX
  UCSR0B |= 1<<TXEN0;
  //enable the UART RX
  UCSR0B |= 1<<RXEN0;
}

void setup_adc()
{
  //8 bit conversion
  ADMUX |= 0x20;
  //AREF External Reference
  ADMUX &= 0x3F;
  //Select the ADC channel
  ADMUX &= 0xF0;
  ADMUX |= CH;
  //enable the ADC
  //Note, this instruction takes 12 ADC clocks to execute
  ADCSRA |= 0x80;
  //enable auto-triggering.
  ADCSRA |= 0x20;
  //free running mode
  ADCSRB &= 0xF8;
  //1MHz ADC frequency
  ADCSRA |= 0x04;
  ADCSRA &= 0xFC;
}

void SetADC(uint8_t freq)
{
  if(freq == F_1M)
  {
    //1MHz ADC frequency
    ADCSRA |= 0x04;
    ADCSRA &= 0xFC;
  }
  else if(freq == F_500k)
  {
    //500kHz ADC frequency
    ADCSRA |= 0x05;
    ADCSRA &= 0xFD;
  }
  else if(freq == F_250k)
  {
    //250kHz ADC frequency
    ADCSRA |= 0x06;
    ADCSRA &= 0xFE;
  }
  else if(freq == F_125k)
  {
    //125kHz ADC frequency
    ADCSRA |= 0x07;
  }
}

void ADCInterruptEnable()
{
  cli();
  //enable the interrupt
  ADCSRA |= 1<<ADIE;
  sei();
}

void uartTxInterruptEnable()
{
  cli();
  //enable the UART TX interrupt
  UCSR0B |= 1<<TXCIE0;//TXCIE0;
  sei();
}

void uartRxInterruptEnable()
{
  cli();
  //enable the UART RX interrupt
  UCSR0B |= 0x80;
  sei();
}

void uartRxInterruptDisable()
{
  cli();
  //disable the UART RX interrupt
  UCSR0B &= 0x7F;
  sei();
}

void uartTxInterruptDisable()
{
  cli();
  //disable the UART TX interrupt
  UCSR0B &= 0xBF;
  sei();
}

ISR(USART0_TX_vect)
{
  if(count_sample >= BUFFER_SIZE) count_sample = 0;
  if(acquisition_buffer_ptr >= BUFFER_SIZE)
  {
    cli();
    end_flag = 1;
    UCSR0B &= 0xBF;
    sei();
  }
  else
  {
    UDR0 = acquisition_buffer[count_sample];
    count_sample++;
    acquisition_buffer_ptr++;
  }
}

ISR(USART0_RX_vect)
{
  //circular buffer to avoid overflow
  if(uart_buffer_ptr >= COMMAND_SIZE)uart_buffer_ptr = 0;
   command[uart_buffer_ptr] = UDR0;
   uart_buffer_ptr++;
}

void StartADC()
{
  ADCSRA |= 1<<ADSC;
}

// Interrupt service routine for the ADC
ISR(ADC_vect)
{
  uint8_t sample = 0;
  static uint8_t tr_on = 0;
  acquisition_buffer[acquisition_buffer_ptr] = ADCH;
  sample = acquisition_buffer[acquisition_buffer_ptr];
  acquisition_buffer_ptr++;
  if(tr_on == 1) count_sample++;
  if((acquisition_buffer_ptr >= BUFFER_SIZE && (command[1] & 0x80) == TRIGGER_OFF) || (count_sample >= (BUFFER_SIZE - ((command[3] << 8 ) | command[4]) - 1) && (command[1] & 0x80) == TRIGGER_ON) )
  {
    tr_on = 0;
    end_flag = 1;
    cli();
    ADCSRA &= 0xF7;
    sei();
  }
  if(tr_on == 0)
  {
      if((sample < command[2] && last_sample >= command[2] && (command[1] & 0x70) == FALLING_EDGE) || (sample > command[2] && last_sample <= command[2] && (command[1] & 0x70) == RISING_EDGE))
      {
         start_sample_pos_h = acquisition_buffer_ptr >> 8;
         start_sample_pos_l = acquisition_buffer_ptr & 0x00FF;
         count_sample = 0;
         tr_on = 1;
      }
    last_sample = sample;
  }
  if(acquisition_buffer_ptr >= BUFFER_SIZE) acquisition_buffer_ptr = 0;
}


void setup()
{
  //peripheral setup
  setup_uart();
  setup_adc();
  uartRxInterruptEnable();
  uartTxInterruptDisable();
  
  //state initialization
  state = GET_CMD;
  
  //variables initialization
  uart_buffer_ptr = 0;
  end_flag = 0;
  end_flag = 0;
  count_sample = 0;
  acquisition_buffer_ptr = 0;
}


void loop()
{
      if(state == GET_CMD)
        if(uart_buffer_ptr >= 1)
          if(command[0] == START_CMD)
            state = GET_2_BYTE;
          else if(command[0] == DATA_CMD)
            state = WAIT_DATA;
          else
            uart_buffer_ptr = 0;
        else
          state = GET_CMD;
      else if(state == GET_2_BYTE) 
        if(uart_buffer_ptr >= COMMAND_SIZE)
          state = ADC_START;
        else
          state == GET_2_BYTE;
      else if(state == ADC_START)
      {
        uartRxInterruptDisable();
        uart_buffer_ptr = 0;
        if((command[1] & 0x70) == FALLING_EDGE)
          last_sample = 0x00;
        else
          last_sample = 0xFF;
        acquisition_buffer_ptr = 0;
        count_sample = 0;
        start_sample_pos_l = 0;
        start_sample_pos_h = 0;
        uartTxInterruptDisable();
        UDR0 = ACK_CMD;
        end_flag = 0;
        SetADC(command[1] & 0x0F);
        StartADC(); //no effect after the first iteration
        ADCInterruptEnable();
        state = ADC_CONV;
      }
      else if(state == ADC_CONV)
      {
        state = ADC_CONV;
        if(end_flag == 1)
        {
          UDR0 = ACK_CMD;
          count_sample = start_sample_pos_l | start_sample_pos_h << 8; 
          count_sample = count_sample - 1;
          //prepere to receive the data command
          state = WAIT_DATA;
          acquisition_buffer_ptr = 0;
          uart_buffer_ptr = 0;
          end_flag = 0;       
          uartRxInterruptEnable();
        }
      }
      else if(state == WAIT_DATA)
      {
        state = WAIT_DATA;
        if(uart_buffer_ptr >= COMMAND_SIZE)
        {
           state = WAIT_DATA;
           acquisition_buffer_ptr = 0;
           state = GET_CMD;
           end_flag = 0;
           count_sample = 0;
        }
        else if(uart_buffer_ptr >= 1)
        {
          if(command[0] == DATA_CMD)
          {
            state = SEND_DATA;
            uartRxInterruptDisable();
            uartTxInterruptEnable();
            acquisition_buffer_ptr = 1;
            UDR0 = acquisition_buffer[count_sample];
            count_sample++;
            uartTxInterruptEnable();
          }
          else
            uart_buffer_ptr = 0;
        }
      }
      else if(state == SEND_DATA)
      {
        state = SEND_DATA;
        if(end_flag == 0x01)
        {
          command[0] = 0x00;
          command[1] = 0x00;
          command[2] = 0x00;
          command[3] = 0x00;
          command[4] = 0x00;
          acquisition_buffer_ptr = 0;
          uart_buffer_ptr = 0;
          state = GET_CMD; 
          uartTxInterruptDisable();
          uartRxInterruptEnable();
          end_flag = 0;
          count_sample = 0;
        }
      }
}

