#!/usr/bin/python

import json
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, request, jsonify
from azure.storage.table import TableService, Entity
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

table_service = TableService(account_name='practohackathon', account_key='T0CPsiGqeUN0vGKLCx4PiULnQXUliSDam8fsMn+OaM4S8utw9z6tM3Tvesvql8U/IHPXVLRhjwy2ylaHEnce2g==')

@app.route('/alsochartdata.json')
@app.route('/chartdata.json')
def get_dummy():
    with open('../data/chart-data-dummy.json', 'r') as f:
        d = json.load(f)
        return jsonify(d)

@app.route('/data/steps/<date_range>')
def get_steps(date_range):
    month, year = date_range.split(',')
    return fetch_azure_data(int(month), int(year), 'steps')
    
@app.route('/data/calories/<date_range>')
def get_calories(date_range):
    month, year = date_range.split(',')
    return fetch_azure_data(int(month), int(year), 'calories')

@app.route('/data/heartrate/<date_range>')
def get_heartrate(date_range):
    month, year = date_range.split(',')
    return fetch_azure_data(int(month), int(year), 'heartrate')

@app.route('/data/distance/<date_range>')
def get_distance(date_range):
    month, year = date_range.split(',')
    return fetch_azure_data(int(month), int(year), 'distance')

@app.route('/data/distance/predict/<date_range>')
def get_predicted_value(date_range):
    table_response = get_predicted_data()
    if table_response == []:
        mlwebservice()
    else:
        table_response = get_predicted_data()

def get_predicted_data():
    data_date = str(datetime.now().date())
    filter_template = "RowKey le '{endDate}'"
    filter_value = filter_template.format(endDate = data_date)
    table_response = table_service.query_entities('predictedGraph', filter = filter_value, select='caloriesPrediction,stepsPrediction,distancePrediction')
    return table_response
    

def fetch_azure_data(month, year, data_type, prediction=None):
    end_date = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
    start_date = datetime(year, month, 1)
    filter_template = "date lt {endDate} and date ge {startDate}"
    filter_value = filter_template.format(endDate = end_date.strftime('%s'), startDate = start_date.strftime('%s'))
    table_response = table_service.query_entities('userGoogleFitData', filter = filter_value, select='distance,steps,heartrate,calories,date,PartitionKey')
    results = []
    username = ''
    for i, response in enumerate(table_response):
        if i == 0:
            username = response['PartitionKey']
        results.append([response['date']* 10 **3, response[data_type]])
    return fill_json(results, data_type, start_date, username)

def fill_json(results, data_type, start_date, username, prediction=None):
    month = start_date.strftime('%b')
    year = start_date.strftime('%Y')
    with open('../data/chart-raw.json', 'r') as f:
        data = json.load(f)
    data['title']['text'] = data['title']['text'].format(username=username, activity=data_type)
    data['subtitle']['text'] = data['subtitle']['text'].format(month=month, year=year)
    data['yAxis']['title']['text'] = data['yAxis']['title']['text'].format(activity=data_type)
    data['series'][0]['name'] = data['series'][0]['name'].format(
        activity=data_type,
        month=month,
        year=year)
    data['series'][0]['data'] = results
    if data_type == 'heartrate':
        with open('../data/anomaly.json', 'r') as f:
            anomaly = json.load(f)
        anomaly_js = {}
        anomaly_js['name'] = 'Anomaly'
        anomaly_js['data'] = anomaly
        data['series'].append(anomaly_js)
    return jsonify(data)

def mlwebservice():
    url = "https://ussouthcentral.services.azureml.net/subscriptions/c466abac2da44d728c5011f292f37e01/services/244022f1079b4e97bb7e36de22186b59/execute?api-version=2.0"
    api_key = 'mWZCd1SLVTP8b9dsI5hd4iQmJF6Q88aLSXdF9hgDuWiwpmxI8w6qUGmBZqa7RGcMKxCmaKtGjVDG7pjQDzJ/Nw=='
    headers = {'Content-Type':'application/json', 'Authorization':('Bearer '+ api_key)}
    body = {
        "Inputs":{},
        "GlobalParameters":{
            "Table name":"userGoogleFitData",
            "SQLQueryScriptFilterData":"select *,date(t1.SummaryDate, '+7 day') as PredictedDate,'tusharka' as CustomerId, date('{summary_date}') as lastSummary  from t1 where t1.SummaryDate < datetime('{summary_date}')"
        }
    }
    body['GlobalParameters']['SQLQueryScriptFilterData'] = body['GlobalParameters']['SQLQueryScriptFilterData'].format(summary_date=str(datetime.now().date()))
    response = requests.post(url, data=json.dumps(body), headers=headers)

@app.route('/data/score/<date_range>')
def get_average_data(date_range):
    month, year = date_range.split(',')
    with open('../data/score_data.json', 'r') as f:
        data = json.load(f)
    # res = {}
    res = round(data[year][month]['total'], 1)
    # res['relative'] = get_relative_insights(month, year)
    return jsonify(res)

@app.route('/data/insights/<date_range>')
def get_relative_insights(date_range):
    month, year = date_range.split(',')
    dates = []
    date_gen = ['{}01', '{}02', '{}03', '{}04', '{}05', '{}06', '{}07', '{}08', '{}09', '{}10', '{}11', '{}12']
    map(lambda x: dates.append([i.format(x) for i in date_gen]), [2016,2017])
    dates = dates[0] + dates[1]
    dates.sort()
    print dates
    ind = dates.index(year+month)
    last_six = dates[max(0, ind-6):ind]
    last_six_data = {}
    with open('../data/average_data_src.json', 'r') as f:
        data = json.load(f)
    for entry in last_six:
        month = entry[4:]
        year = entry[:4]
        entry = data[year][month]
        for key, value in entry.items():
            if key not in last_six_data:
                last_six_data[key] = value
            else:
                last_six_data[key] += value
    for keys in last_six:
        last_six_data[key]= round((last_six_data[key]/6.0),1)
    prev = dates[max(0, ind-1)]
    prev_data = data[prev[:4]][prev[4:]]
    res = {}
    # res['last_six'] = last_six_data
    res['last'] = prev_data
    return jsonify(res)

        
@app.errorhandler(404)
def page_not_found(e):
    return "Not found", 404

@app.errorhandler(400)
def bad_request(e):
    return "Bad request", 400

if __name__ == "__main__":
    app.run(port = 7089, debug=True, host='0.0.0.0')
