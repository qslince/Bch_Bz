# Bch_Bz
Best team for Hack&amp;Change Hackathon
This web application was developed based on the case of the Moscow transport government

# Usage

!!! U need python3.10 !!!


1. Clone this rep.:
```
git clone https://github.com/qslince/Bch_Bz.git
cd Bch_bz
git switch test
```
2. Setup virtual environments:
```
source venv/bin/activate
```

3. Install the required libraries listed in `requirements.txt` file using `pip`:

```
pip install -r requirements.txt
```
4. Run `main.py` to create server.

```
uvicorn app.main:app --reload
```
