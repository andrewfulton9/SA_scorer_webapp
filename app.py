import os
from flask import Flask, flash, render_template, request, redirect, \
                  url_for, session, send_file
from flask.ext.session import Session
from werkzeug.utils import secure_filename
import cPickle as pickle
import pandas as pd
from score_code import sa
import tempfile
import os
import json
import sys
import numpy as np

ALLOWED_EXTENSIONS = set(['xlsx', 'xlsm', 'xlt'])

app = Flask(__name__)
sess = Session()

with open('key.json') as f:
    key_file = json.load(f)

app.secret_key = key_file['secret_key']
app.config['SESSION_TYPE'] = 'filesystem'

sess.init_app(app)

def allowed_file(filename):
    '''
    input: filename
    output: True or False

    checks to make sure an uploaded file is included in allowed filenames
    '''
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def convert_index(df):
    '''
    input: dataframe
    output: dataframe

    changes index values to strings
    '''
    new_ix = [str(i) for i in df.index]
    df.index = new_ix
    return df

def get_weight_perc(df):
    '''
    input: df
    output: Series

    calculates weight percentages based on pre and post weights if in
    dataframe. Otherwise returns empty strings
    '''
    if False in df['pre_weight'].isnull().values and \
       False in df['post_weight'].isnull().values:
        weight_percentage = df['post_weight'] / df['pre_weight']
    else:
        weight_percentage = pd.Series(['' for ix in df.index],
                                      index = df.index)
    weight_percentage.name = 'weight_percentage'
    return weight_percentage

def get_group(df):
    if False in df['group'].isnull().values:
        group = df['group']
        has_groups = True
    else:
        group = pd.Series(['' for ix in df.index], index = df.index)
        has_groups = False
    group.name = 'group'
    return group, has_groups

def build_scored_df(filename, rescore=None):
    # builds the scored dataframe
    df = pd.read_excel(filename, 'Sheet1', index_col = 0, header = 0)
    df = convert_index(df)
    weight_percentage = get_weight_perc(df)
    group, has_groups = get_group(df)

    # handles rescoring
    if rescore == 'full':
        scored = sa(df)
    elif rescore == 'score_6':
        scored = sa(df, rescore6 = True)
    elif rescore == 'score_12':
        scored = sa(df, rescore12 = True)

    scored = pd.concat([group, weight_percentage, scored], axis=1)
    scored = scored.dropna(thresh = 6, axis = 0)
    return scored, has_groups

def stdev_2_stderror(describe_df):
    dt = describe_df.T.copy()
    for x in dt.columns.levels[0]:
        count = dt[x]['count'][0]
        dt[x, 'std'] = dt[x]['std'].div(np.sqrt(count))

    new_levels = [name if name != 'std' else 'sterr' for name in dt.columns.levels[1]]
    dt.columns.set_levels(new_levels, level=1, inplace = True)
    return dt.T

def get_descriptive_stats(df):
    grouped = df.groupby('group').describe()
    grouped = stdev_2_stderror(grouped)
    return grouped

@app.route('/', methods = ['GET'])
@app.route('/home', methods = ['GET'])
def home():
    # site home page
    return render_template('home.html')

@app.route('/upload', methods=['GET','POST'])
def upload():
    # page to upload file to be scored
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('file upload problem, please retry')
            return redirect(request.url)
        f = request.files['file']
        if f.filename == '':
            flash('no selected file')
            return redirect(request.url)
        if f:
            if allowed_file(f.filename):
                rescore = request.form['rescore']
                filename = secure_filename(f.filename)
                UPLOAD_FOLDER = '/tmp'
                session['UPLOAD_FOLDER'] = UPLOAD_FOLDER
                session['filename'] = filename
                session['rescore'] = rescore
                f.save(os.path.join(UPLOAD_FOLDER, filename))
                return redirect(url_for('results'))
            else:
                flash('improper file type. Must be an Excel file')
                return redirect(request.url)
    return render_template('upload.html')

@app.route('/results', methods=['GET'])
def results():
    # page to process uploaded file and display results
    UPLOAD_FOLDER = session.get('UPLOAD_FOLDER')
    name = session.get('filename')
    rescore = session.get('rescore')
    path = UPLOAD_FOLDER + '/' + name
    # use try/except here since file is deleted immediatly after being processed
    # if user try's to reload it will redirect them to upload page
    if os.path.exists(path):
        try:
            scored_df, has_groups = build_scored_df(path, rescore = rescore)
            save_name = 'scored_{}.csv'.format(name[:-5])
            saved_results = scored_df.to_csv(UPLOAD_FOLDER + '/' + save_name)
            session['scored_path'] = UPLOAD_FOLDER + '/' + save_name
            session['scored_filename'] = save_name
            os.remove(path)
            if has_groups:
                described = get_descriptive_stats(scored_df)
                return render_template('results.html', name=name,
                                       f = scored_df.to_html(),
                                       f1 = described.to_html(),
                                       describe = has_groups)
            else:
                return render_template('results.html', name=name,
                                       f = scored_df.to_html(),
                                       describe = has_groups)
        except:
            flash('error processing file. Please ensure you \
                   are following template')
            return redirect(url_for('upload'))
    else:
        flash('Please reupload file')
        return redirect(url_for('upload'))

@app.route('/download', methods = ['GET', 'POST'])
def download():
    # download page to download template and example files
    if request.method == 'POST':
        if request.form['submit'] == 'download example':
            return send_file('test_files/test.xlsx',
                             as_attachment = True,
                             attachment_filename = 'sa_example.xlsx')
        elif request.form['submit'] == 'download template':
            return send_file('test_files/excel_template.xlsx',
                             as_attachment = True,
                             attachment_filename = 'sa_template.xlsx')

@app.route('/download_results', methods = ['GET', 'POST'])
def download_results():
    # download page to download results
    scored_path = session.get('scored_path')
    scored_name = session.get('scored_filename')
    return send_file(scored_path,
                     as_attachment = True,
                     attachment_filename=scored_name)




if __name__ == '__main__':
    sess.init_app(app)
    app.run(debug = True)
