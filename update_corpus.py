import re
import requests
import sys

if len(sys.argv) < 3:
    print (
        "Usage: python update_corpus.py input_corpus_file " +
        "output_dict_file output_lm_file")
    sys.exit(1)

url = "http://www.speech.cs.cmu.edu/cgi-bin/tools/lmtool/run"
files = {"corpus": open(sys.argv[1], "rb")}
r = requests.post(url, files=files, data={"formtype": "simple"})

m = re.search(r"\d{4}.dic", r.content)
dic_file = m.group(0)

r_dic = requests.get(r.url + dic_file)
with open(sys.argv[2], "w") as f:
    f.write(r_dic.content)

lm_file = dic_file.replace("dic", "lm")
r_lm = requests.get(r.url + lm_file)
with open(sys.argv[3], "w") as f:
    f.write(r_lm.content)

print "Updated corpus"
