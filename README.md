Install libraries and dependencies using

```
pip install -r requirements-dev.txt
```
...


To run Tests, run:

(For Mac/Linux in one line)

```
ALPACA_API_KEY=dummy ALPACA_SECRET_KEY=dummy DATABASE_URL=sqlite:///./test.db python -m pytest
```

(Windows Powershell)

```
$env:ALPACA_API_KEY="dummy"; $env:ALPACA_SECRET_KEY="dummy";

$env:DATABASE_URL="sqlite:///./test.db"; python -m pytest
```