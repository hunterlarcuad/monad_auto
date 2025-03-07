# Monad
NFT Mint on magiceden.io

# venv
```
# Create venv
python3 -m venv venv
# Activate venv
source venv/bin/activate
# Exit venv
deactivate
```

# Install
```
pip install --upgrade pip
pip install -r requirements.txt
```

# Run
```
cd monad_auto/
cp conf.py.sample conf.py
cp datas/purse/purse.csv.sample datas/purse/purse.csv
# modify datas/purse/purse.csv
python monad_auto.py
```
