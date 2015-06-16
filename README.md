# Lightweight-Arduino-Scope
Plug and play DAQ system based on the Arduino board that requires only 48 bytes of RAM to run increasing the number of samples that can be acquired. The acquired samples are transfered to the PC with the serial port at 1Mbaud/s.
No external hardware is needed for the TRIGGER.

Arduino Uno
- 1 Channel
- Sampling frequency (max) 76.9 kHz
- Resolution 8 bit 
- 2000 samples at each time
- Free Run mode or Trigger mode with the trigger level, trigger delay and trigger edge configurable by serial commands

Arduino Mega 2560
- 1 Channel
- Sampling frequency (max) 76.9 kHz
- Resolution 8 bit 
- 8000 samples at each time
- Free Run mode or Trigger mode with the trigger level, trigger delay and trigger edge configurable by serial commands

A simple interface for the signal acquisition has been developed in Python, for more information please refer to the Wiki pages.

