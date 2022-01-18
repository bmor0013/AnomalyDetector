import enum
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
ls = []
ls1 = []
ls2 = []
apikey = '639d4273d8ce41d5941f30428248fc4f' 
endpoint = 'https://eastus.api.cognitive.microsoft.com/anomalydetector/v1.0/timeseries/entire/detect'
def detect(endpoint, apikey, request_data):
    headers = {'Content-Type': 'application/json', 'Ocp-Apim-Subscription-Key': apikey}
    response = requests.post(endpoint, data=json.dumps(request_data), headers=headers)
    if response.status_code == 200:
        return json.loads(response.content.decode("utf-8"))
    else:
        print(response.status_code)
        raise Exception(response.text)


def build_figure(sample_data, sensitivity):
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

def main(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob \n"
                 f"Name: {myblob.name}\n"
                 f"Blob Size: {myblob.length} bytes")
    
    # logging.info(str(myblob.read()))
    # var = str(myblob.read())
    var = myblob.read()
    var = var.decode("utf-8") 
    # var = var.split('}')
    ls.append(var)
    var = ls[0]
    var = var.split('\n') # creates all the logs
    print(json.loads(var[0])['time'])
    # ls = []
    # var = json.loads(json.loads(i)['properties'])['CsBytes'] # dict within a dict, first properties indexed converted to a dict then the metric CsBytes extracted
    # print(json.loads(json.loads(var[0])['properties'])['CsBytes'])
    print(len(var))
    ls1 = []
    i = 0

    while i < len(var):

        # print(i)
        if i> 1 and str(json.loads(var[i])['time']) != str(json.loads(var[i-1])['time']):
            ls1.append(int(json.loads(json.loads(var[i])['properties'])['CsBytes']))
            ls2.append(str(json.loads(var[i])['time']))
        if i == len(var)-2:
            break
        i+=1
        # if i == None:
            # ls1.append(json.loads(json.loads(i)['properties'])['CsBytes'])
    
    sample_data = {'granularity':'secondly'}
    sample_data['series'] = []
    prev = None
    for i in range(0,len(ls1)):
        v =  datetime.fromisoformat(ls2[i])
        v = v.strftime("%d/%m/%Y %H:%M:%S")
        if i > 0 and str(v) != prev:
            sample_data['series'].append({'timestamp':str(v), 'value':ls1[i] })
        prev = str(v)
    # print(len(ls1))
    print(sample_data)

    build_figure(sample_data,95)
