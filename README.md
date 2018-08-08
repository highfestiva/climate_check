# climate_check.py

A no-nonsense climate checker. It downloads all monthly mean air temperatures from SMHI (Sweden's institute
of meteorology) and calculates the temperature increase since measurements started. Note that SMHI always
leaves out the last four months, as they are "unverified".

This check might be considered unscientific as I am only using Swedish air temperature, not world-wide air
and ocean temperatures.


## Usage

```bash
$ ./climate_check.py

...

downloading new data from SMHI:
  medel, 1 gång per månad
  Lufttemperatur - Övre Gränsö
loading station data:
  99 %  Söderarm A
971 stations counted.
Temperature in Sweden is up by 0.1 degrees C since 1732.
```

## Result

![climate-unchange](https://raw.githubusercontent.com/highfestiva/climate_check/master/readme-img/climate-unchange.png)

Are you stumped too? If you find any bugs, let me know or add a pull request. Spread the word.


## Licence

MIT
