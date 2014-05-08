import re
import requests

url = "http://www.speech.cs.cmu.edu/cgi-bin/tools/lmtool/run"
files = {"corpus": open("/home/pi/chattypi/data/corpus_final.txt", "rb")}
r = requests.post(url, files=files, data={"formtype": "simple"})

m = re.search(r"\d{4}.dic", r.content)
dic_file = m.group(0)

r_dic = requests.get(r.url + dic_file)
with open("/home/pi/chattypi/data/sample.dic", "w") as f:
    f.write(r_dic.content)

lm_file = dic_file.replace("dic", "lm")
r_lm = requests.get(r.url + lm_file)
with open("/home/pi/chattypi/data/sample.lm", "w") as f:
    f.write(r_lm.content)

print "Updated corpus"
