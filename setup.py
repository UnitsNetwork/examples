from setuptools import setup, find_packages

setup(
    name="units_network",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "units_network": ["bridge-abi.json"],
    },
    scripts=[
        "bin/transfer-c2e.py",
        "bin/transfer-e2c.py",
        "bin/transfer-e2c-withdraw.py",
    ],
    install_requires=["pywaves==1.0.5", "web3==7.2.0", "pymerkle==6.1.0"],
    description="Scripts and classes to interact with Unit0",
    url="https://github.com/UnitsNetwork/examples",
)
