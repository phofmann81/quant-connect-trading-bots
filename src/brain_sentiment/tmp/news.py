algo = ["EQT", "MPWR", "HCWB", "FICO", "MPC"]


tf = [
    "US500",
    "US100",
    "US30",
    "WSM",
    "GLBE",
    "ZIM",
    "KEYS",
    "FLEX",
    "ZI",
    "CHWY",
    "QFIN",
    "NWL",
    "VKTX",
    "YMM",
    "APP",
    "TTD",
    "LNTH",
    "CMCSA",
    "SQM",
    "TJX",
    "OKLO",
    "NIO",
    "TGT",
]

intersection = list(set(algo) & set(tf))

print(intersection)
