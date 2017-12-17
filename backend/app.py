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


def fetch_azure_data(month, year, data_type):
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

def fill_json(results, data_type, start_date, username):
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
    return jsonify(data)
        
@app.errorhandler(404)
def page_not_found(e):
    return "Not found", 404

@app.errorhandler(400)
def bad_request(e):
    return "Bad request", 400

if __name__ == "__main__":
    app.run(port = 7089, debug=True, host='0.0.0.0')
