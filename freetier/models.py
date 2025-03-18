import sys
from modelGroq import modelGroq
from modelOllama import modelOllama
from modelGemini import modelGemini
from modelCloudflare import modelCloudflare

mod = int(sys.argv[2])

def cm():
    return modelCloudflare[mod];

def gm():
    return modelGemini[mod];

def om():
    return modelOllama[mod];

def qm():
    return modelGroq[mod];