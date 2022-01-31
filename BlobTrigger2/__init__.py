import enum
from datetime import datetime, timedelta
import logging
import http.client, urllib.request, urllib.parse, urllib.error, base64
from random import sample
# import azure.functions as func
import json
import azure.functions as func
import requests # had to install
import json
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Import library to display results
import matplotlib.pyplot as plt
# %matplotlib inline 
from bokeh.plotting import figure,output_notebook, show
from bokeh.palettes import Blues4
from bokeh.models import ColumnDataSource,Slider

# import datetime
from datetime import datetime
from bokeh.io import push_notebook
from dateutil import parser
from ipywidgets import interact, widgets, fixed


apikey = '34442f5a16554d4eb8a6761c867d2f5a' 
endpoint = 'https://eastus.api.cognitive.microsoft.com/anomalydetector/v1.0/timeseries/entire/detect'
current_values = []
last_upload = None
def detect(endpoint, apikey, request_data):
    headers = {'Content-Type': 'application/json', 'Ocp-Apim-Subscription-Key': apikey}
    response = requests.post(endpoint, data=json.dumps(request_data), headers=headers)
    if response.status_code == 200:
        return json.loads(response.content.decode("utf-8"))
    else:
        print(response.status_code)
        raise Exception(response.text)


def build_figure(sample_data, sensitivity,target):
  sample_data['sensitivity'] = sensitivity
  # print(sample_data)
  result = detect(endpoint, apikey, sample_data)
  # print(result)
  columns = {'expectedValues': result['expectedValues'], 'isAnomaly': result['isAnomaly'], 'isNegativeAnomaly': result['isNegativeAnomaly'],
     'isPositiveAnomaly': result['isPositiveAnomaly'], 'upperMargins': result['upperMargins'], 'lowerMargins': result['lowerMargins'],
     'timestamp': [parser.parse(x['timestamp']) for x in sample_data['series']],
     'value': [x['value'] for x in sample_data['series']]}
  response = pd.DataFrame(data=columns)
  # print(response)
  values = response['value']
  label = response['timestamp']
  anomalies = []
  anomaly_labels = []
  index = 0
  anomaly_indexes = []
  p = figure(x_axis_type='datetime', title="Batch Anomaly Detection ({0} Sensitvity)".format(sensitivity), width=800, height=600)
  for anom in response['isAnomaly']:
    if anom == True and (float(values[index]) > response.iloc[index]['expectedValues'] + response.iloc[index]['upperMargins'] or
             float(values[index]) < response.iloc[index]['expectedValues'] - response.iloc[index]['lowerMargins']):
      anomalies.append(float(values[index]))
      anomaly_labels.append(label[index])
      anomaly_indexes.append(index)
    index = index+1
#   print(anomalies)
#   print(anomaly_labels)
#   print(anomaly_indexes)
  target["anomalies"] = anomalies
  anomaly_labels_copy = []
  for i in anomaly_labels:
      anomaly_labels_copy.append(i.strftime("%d/%m/%Y %H:%M:%S"))
  target["anomaly_labels"] = anomaly_labels_copy
  target["anomaly_indexes"] = anomaly_indexes


  upperband = response['expectedValues'] + response['upperMargins']
  lowerband = response['expectedValues'] -response['lowerMargins']
  band_x = np.append(label, label[::-1])
  band_y = np.append(lowerband, upperband[::-1])
  boundary = p.patch(band_x, band_y, color=Blues4[2], fill_alpha=0.5, line_width=1, legend='Boundary')
  p.line(label, values, legend='Value', color="#2222AA", line_width=1)
  p.line(label, response['expectedValues'], legend='ExpectedValue', line_width=1, line_dash="dotdash", line_color='olivedrab')
  anom_source = ColumnDataSource(dict(x=anomaly_labels, y=anomalies))
  anoms = p.circle('x', 'y', size=5, color='tomato', source=anom_source)
  p.legend.border_line_width = 1
  p.legend.background_fill_alpha = 0.1
  show(p, notebook_handle=True)
  return target



def main(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob \n"
                 f"Name: {myblob.name}\n"
                 f"Blob Size: {myblob.length} bytes")
    
    var = myblob.read()
    var = var.decode("utf-8") 
    var = var.split('\r\n')
    ls = []

    metrics = ["CpuTime","BytesSent","HttpResponseTime"]
    metric_ls = []

    for metric in metrics:
        var_temp = []
        i=0
        while i < len(var):
            temp =json.loads(var[i])
            if temp["metricName"] == metric:
                var_temp.append(json.loads(var[i])) # values of CPU Time
            #time = var_temp[i]["time"]
            #time = time[0:18]
            #var_temp[i]["time"]= time
            if i == len(var)-2:
                break
            i+=1
        metric_ls.append({
            "name" : metric,
            "json" : var_temp
        })
    

    
    # sorted(var_temp, key=lambda var_temp:var_temp["time"])
    #print(var_temp)
    #print(len(var))

    metric_ls_1 = []
    for metric in metric_ls:

        ls1 = []
        ls2 = []
        i = 0

        while i < len(metric["json"]):
            if i> 1 and str(metric["json"][i]['time']) != str(metric["json"][i-1]['time']):
                ls1.append(float(metric["json"][i]['average']))
                ls2.append(str(metric["json"][i]['time']))
            if i == len(metric["json"])-2:
                break
            i+=1
        metric_ls_1.append({"name": metric["name"], "time" : ls2, "values" : ls1 })
    
    
    metric_ls_2 = []
    for metric in metric_ls_1:
        sample_data = {'granularity':'secondly'}
        sample_data['series'] = []
        prev = None
        for i in range(0,len(metric["values"])):
            newstring = ls2[i][0:18]+'Z'
            v = datetime.strptime(newstring, '%Y-%m-%dT%H:%M:%SZ')
            v = v.strftime("%d/%m/%Y %H:%M:%S")
            # v =  datetime.fromisoformat(metric["time"][i])
            # v = v.strftime("%d/%m/%Y %H:%M:%S")
            if i > 0 and str(v) != prev:
                sample_data['series'].append({'timestamp':str(v), 'value':metric["values"][i] })
            prev = str(v)
        metric_ls_2.append(sample_data)


    current_values.append(metric_ls_2)
    past = datetime.now() - timedelta(days=1)
    global last_upload

    if past > last_upload:

        target = {
            "name":"insights-metrics-pt1m",
            "data" : []
        }    
        for i in range(0, len(metric_ls_2)):
            obj = {
                "anomalies":[],
                "anomaly_labels": [],
                "anomaly_indexes" : []
            }
            result = build_figure(metric_ls_2[i],95,obj)
            target["data"].append({
                "metricName" : metrics[i],
                "anomalies" : result
                }            
            )

        url = "https://aiopsendpoint.azurewebsites.net/"#"http://192.168.68.107:5000/"#"https://aiopsendpoint.azurewebsites.net/"
        # response = requests.post(url, target)
        response = requests.post(url, json.dumps(target))
        last_upload = datetime.now()


