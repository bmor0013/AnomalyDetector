from cgitb import reset
import enum
import logging
import http.client, urllib.request, urllib.parse, urllib.error, base64
from time import time
from random import sample
# import azure.functions as func
import json
import azure.functions as func
import requests # had to install
import json
import pandas as pd
import numpy as np
import warnings
from datetime import datetime, timedelta

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
# ls = []
# ls1 = []
# ls2 = []
apikey = '639d4273d8ce41d5941f30428248fc4f' 
endpoint = 'https://eastus.api.cognitive.microsoft.com/anomalydetector/v1.0/timeseries/entire/detect'


current_values = []
last_upload =  None


current_values = []
last_upload = datetime.now() 




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
    p.line(label, values, legend='Value', color="#2222aa", line_width=1)
    p.line(label, response['expectedValues'], legend='ExpectedValue',  line_width=1, line_dash="dotdash", line_color='olivedrab')
    anom_source = ColumnDataSource(dict(x=anomaly_labels, y=anomalies))
    anoms = p.circle('x', 'y', size=5, color='tomato', source=anom_source)
    p.legend.border_line_width = 1
    p.legend.background_fill_alpha  = 0.1
    show(p, notebook_handle=True)
    return target
def main(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob \n"
                 f"Name: {myblob.name}\n"
                 f"Blob Size: {myblob.length} bytes")

    var = myblob.read()
    var = var.decode("utf-8") 
    ls = []
    ls.append(var)
    var = ls[0]
    var = var.split('\n') # creates all the logs


    metrics = ["CsBytes","ScStatus","TimeTaken"]
    metric_ls = []

    for metric in metrics:
        i = 0
        ls1 = []
        ls2 = []
        while i < len(var):
            # print(i)
            if i> 1 and str(json.loads(var[i])['time']) != str(json.loads(var[i-1])['time']):
                ls1.append(int(json.loads(json.loads(var[i])['properties'])[metric]))
                ls2.append(str(json.loads(var[i])['time']))
            if i == len(var)-2:
                break
            i+=1
        metric_ls.append({"name": metric, "time" : ls2, "values" : ls1 })
    

    metric_ls_2 = []
    for metric in metric_ls:
        sample_data = {'granularity':'secondly'}
        sample_data['series'] = []
        prev = None
        for i in range(0,len(metric["values"])):
            v =  datetime.fromisoformat(metric["time"][i])
            v = v.strftime("%d/%m/%Y %H:%M:%S")
            if i > 0 and str(v) != prev:
                sample_data['series'].append({'timestamp':str(v), 'value':metric["values"][i] })
            prev = str(v)
        metric_ls_2.append(sample_data)


    # print(len(ls1))
    # target = {
    # "name":"insights-logs-appservicehttplogs",
    # "data": 
    #     {"anomalies":[],
    #     "anomaly_labels" : [],
    #     "anomaly_indexes" : []
    #     }
    # }

    # print(sample_data)
    current = datetime.now()
    global last_upload

    if current - timedelta(minutes = 5) >= last_upload:
        target = {
            "name":"insights-logs-appservicehttplogs",
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
        print(target)

        url = "https://aiopsendpoint.azurewebsites.net/"#"http://192.168.68.107:5000/"#"https://aiopsendpoint.azurewebsites.net/"
        # response = requests.post(url, target)
        response = requests.post(url, json.dumps(target))
        last_upload = current
        print(response)
    # current_values.append(metric_ls_2)
    # past = datetime.now() - timedelta(days=1)
    # global last_upload

    # if past > last_upload:

    #     target = {
    #         "name":"insights-metrics-pt1m",
    #         "data" : []
    #     }    
    #     for i in range(0, len(metric_ls_2)):
    #         obj = {
    #             "anomalies":[],
    #             "anomaly_labels": [],
    #             "anomaly_indexes" : []
    #         }
    #         result = build_figure(metric_ls_2[i],95,obj)
    #         target["data"].append({
    #             "metricName" : metrics[i],
    #             "anomalies" : result
    #             }            
    #         )

    #     url = "https://aiopsendpoint.azurewebsites.net/"#"http://192.168.68.107:5000/"#"https://aiopsendpoint.azurewebsites.net/"
    #     # response = requests.post(url, target)
    #     response = requests.post(url, json.dumps(target))
    #     last_upload = datetime.now()
