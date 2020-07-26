# climate_check.py

A no-nonsense climate checker. It downloads all monthly mean air temperatures from SMHI (Sweden's institute
of meteorology) and calculates the temperature increase since measurements started. Note that SMHI always
leaves out the last four months, as they are "unverified".

This check might be considered unscientific as I am only using Swedish air temperature, not world-wide air
and ocean temperatures.

You will need to `pip install pandas sklearn`.


## Usage

```bash
$ ./climate_check.py

...

loading station data:
  100%  Söderarm A
  911 stations counted.
Average air temperature in Sweden is up by 1.2 degrees C since 1741.
```

## Result

![climate-unchange](https://raw.githubusercontent.com/highfestiva/climate_check/master/readme-img/climate-unchange.png)

If you find any bugs, let me know or add a pull request.


## Licence

MIT
