# -*- coding: utf-8 -*-
import os
import pandas as pd

from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import ui, expected_conditions as ec

import click
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_apscheduler import APScheduler

from pyecharts import options as opts
from pyecharts.charts import Timeline, Map

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.root_path, 'data.db')
app.config['SCHEDULER_API_ENABLED'] = True

db = SQLAlchemy(app)
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, Total=Total, Death=Death)

@app.cli.command()
def resetdb():
    click.echo('Begin...')
    
    db.drop_all()
    db.create_all()
    
    epiTotal = pd.read_csv(os.path.join(basedir, 'rawData\\epiTotal.csv'))
    for index, row in epiTotal.iterrows():
        inserting = Total(name=row['countries'], total=row['total'])
        db.session.add(inserting)
        db.session.commit()
    
    epiDeath = pd.read_csv(os.path.join(basedir, 'rawData\\epiDeath.csv'))
    for index, row in epiDeath.iterrows():
        inserting = Death(name=row['countries'], death=row['death'])
        db.session.add(inserting)
        db.session.commit()
    
    click.echo('Done.')
    
class Total(db.Model):
    country_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    total = db.Column(db.Integer, nullable=False)

class Death(db.Model):
    country_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    death = db.Column(db.Integer, nullable=False)

@scheduler.task('interval', id='job_crawling', max_instances=1, hours=12, start_date='2021-09-03 00:00:00')
def crawling():
    epiTotal = {'countries': [], 'total': []}
    epiDeath = {'countries': [], 'death': []}
    options = ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--window-size=1920,1080')
    driver = Chrome(chrome_options=options)
    
    try:
        driver.get('https://coronavirus.app/map')
        for element in driver.find_elements(
                By.XPATH, '//div[@class="map-sidebar-section-item"]/div[2]/div[1]'):
            epiTotal['countries'].append(element.text)
        for element in driver.find_elements(
                By.XPATH, '//div[@class="map-sidebar-section-item"]/div[3]'):
            epiTotal['total'].append(element.text)
        menu = driver.find_element(By.XPATH, '//span[text()="Total cases"]')
        menu.click()
        wait = ui.WebDriverWait(driver, 1)
        deaths = wait.until(
            ec.element_to_be_clickable((By.XPATH, '//div[text()="Deaths"]')))
        deaths.click()
        if wait.until(
                ec.visibility_of_element_located(
                    (By.XPATH, '//span[text()="Deaths"]'))):
            for element in driver.find_elements(
                    By.XPATH,
                    '//div[@class="map-sidebar-section-item"]/div[2]/div[1]'):
                epiDeath['countries'].append(element.text)
            for element in driver.find_elements(
                    By.XPATH, '//div[@class="map-sidebar-section-item"]/div[3]'):
                epiDeath['death'].append(element.text)
    
    except Exception as error:
        print('error: ', error)
        driver.quit()
    
    else:            
        epiTotal = pd.DataFrame.from_dict(epiTotal, orient='columns')
        epiDeath = pd.DataFrame.from_dict(epiDeath, orient='columns')
        
        epiTotal['total'] = epiTotal['total'].apply(lambda s: int(s.replace(',', '')))
        epiDeath['death'] = epiDeath['death'].apply(lambda s: int(s.replace(',', '')))
        
        db.drop_all()
        db.create_all()
        
        for index, row in epiTotal.iterrows():
            inserting = Total(name=row['countries'], total=row['total'])
            db.session.add(inserting)
            db.session.commit()
            
        for index, row in epiDeath.iterrows():
            inserting = Death(name=row['countries'], death=row['death'])
            db.session.add(inserting)
            db.session.commit()
    
def get_each_chart(_type: str, data: list):
    map_data = [[[x['name'], x['value']] for x in d['data']] for d in data
                if d['type'] == _type][0]
    min_data, max_data = (
        min([d[1][0] for d in map_data]),
        max([d[1][0] for d in map_data]),
    )
    map_chart = (
        Map().add(
            series_name='',
            data_pair=map_data,
            maptype='world',
            label_opts=opts.LabelOpts(is_show=True),
            is_map_symbol_show=False,
            layout_center=['50%', '50%'],
            layout_size='150%',
            itemstyle_opts={
                'normal': {
                    'areaColor': '#323c48',
                    'borderColor': '#404a59'
                },
                'emphasis': {
                    'label': {
                        'show': Timeline
                    },
                },
            },
        ).set_series_opts(label_opts=opts.LabelOpts(is_show=False)).
        set_global_opts(
            legend_opts=opts.LegendOpts(is_show=False),
            tooltip_opts=opts.TooltipOpts(
                is_show=True,
                formatter='{b}:{c}',
            ),
            visualmap_opts=opts.VisualMapOpts(
                is_calculable=True,
                dimension=0,
                orient='vertical',
                pos_left='18',
                pos_top='45%',
                range_text=['Max', 'Min'],
                range_color=['#FFFF70', '#FF3300', '#8B0000'],
                textstyle_opts=opts.TextStyleOpts(color='grey'),
                min_=min_data,
                max_=max_data,
            ),
            graphic_opts=[
                opts.GraphicGroup(
                    graphic_item=opts.GraphicItem(
                        bounding='raw',
                        right='84%',
                        bottom='6%',
                        z=100,
                    ),
                    children=[
                        opts.GraphicRect(
                            graphic_item=opts.GraphicItem(left='center',
                                                          top='center',
                                                          z=100),
                            graphic_shape_opts=opts.GraphicShapeOpts(
                                width=400, height=50),
                            graphic_basicstyle_opts=opts.GraphicBasicStyleOpts(
                                fill='rgba(0,0,0,0.3)'),
                        ),
                        opts.GraphicText(
                            graphic_item=opts.GraphicItem(left='center',
                                                          top='center',
                                                          z=100),
                            graphic_textstyle_opts=opts.GraphicTextStyleOpts(
                                text=f'全球疫情{_type}人数',
                                font='bold 26px Microsoft YaHei',
                                graphic_basicstyle_opts=opts.
                                GraphicBasicStyleOpts(fill='#fff'),
                            ),
                        ),
                    ],
                )
            ],
        )
    )
    
    return map_chart

def get_component_chart():
    epiTotal = {'countries': [], 'total': []}
    epiDeath = {'countries': [], 'death': []}
    
    epitotal, epideath = Total.query.all(), Death.query.all()
    for total, death in zip(epitotal, epideath):
        epiTotal['countries'].append(total.name)
        epiTotal['total'].append(total.total)
        epiDeath['countries'].append(death.name)
        epiDeath['death'].append(death.death)
        
    epiTotal = pd.DataFrame.from_dict(epiTotal, orient='columns')
    epiDeath = pd.DataFrame.from_dict(epiDeath, orient='columns')
    
    lowTotal, highTotal = epiTotal['total'].min(), epiTotal['total'].max()
    dataPairTotal = [[c, v]
                    for c, v in zip(epiTotal['countries'], epiTotal['total'])]
    lowDeath, highDeath = epiDeath['death'].min(), epiDeath['death'].max()
    dataPairDeath = [[c, v]
                    for c, v in zip(epiDeath['countries'], epiDeath['death'])]
                    
    data = [{
        'type': '确诊',
        'data': [{
            'name': d[0],
            'value': [d[1], d[0]]
        } for d in dataPairTotal]
    }, {
        'type': '死亡',
        'data': [{
            'name': d[0],
            'value': [d[1], d[0]]
        } for d in dataPairDeath]
    }]
    
    timeline = Timeline()
    type_list = ['确诊', '死亡']
    for s in type_list:
        g = get_each_chart(s, data)
        timeline.add(g, time_point=s)

    timeline.add_schema(
        is_auto_play=True,
        is_timeline_show=False,
        play_interval=3600
    )
    
    return timeline

@app.route('/')
def index():
    return render_template('index.html')
    
@app.route('/map')
def get_chart():
    timeline = get_component_chart()
    return timeline.dump_options_with_quotes()