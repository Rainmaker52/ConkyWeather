# ConkyWeather
A simple Python script to retrieve location and weather information

ConkyWeather is built on the principle "Better to beg forgiveness than ask permission". Almost everything is encapsulated in try except blocks.
The script uses several different free APIs. Users do not have to have to generate API keys or follow difficult signup procedures.

The script uses the "requests" library for HTTP interactions. This is the only dependency.

Some examples:

- Get current external IP address:
./ConkyWeather.py --externalip

- Get the windspeed for today, for the current location
ConkyWeather.py --local --windspeed --day 0

- Same thing, at my home location
ConkyWeather.py --home --homewoe 727232 --windspeed --day 0

- Get the temperature for tommorrow, at my home location
ConkyWeather.py --home --homewoe 727232 --temperature --day 1

