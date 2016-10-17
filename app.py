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

ALLOWED_EXTENSIONS = set(['xlsx', 'xlsm', 'xlt'])

app = Flask(__name__)
sess = Session()

with open('/home/ubuntu/SA_scorer_webapp/key.json') as f:
    key_file = json.load(f)

app.secret_key = key_file['secret_key']
app.config['SESSION_TYPE'] = 'filesystem'

def allowed_file(filename):
    # checks to see if an uploaded file is of proper filetype
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

def build_scored_df(filename, rescore=None):
    # builds the scored dataframe
    df = pd.read_excel(filename, 'Sheet1', index_col = 0, header = 0)
    df = convert_index(df)
    if df['pre_weight'].empty == False and \
       df['post_weight'].empty == False:
        weight_percentage = df['post_weight'] / df['pre_weight']
        weight_percentage.name = 'weight_percentage'

    # handles rescoring
    if rescore == 'full':
        scored = sa(df)
    elif rescore == 'score_6':
        scored = sa(df, rescore6 = True)
    elif rescore == 'score_12':
        scored = sa(df, rescore12 = True)

    scored = pd.concat([df['group'], weight_percentage, scored], axis=1)
    scored = scored.dropna(thresh = 6, axis = 0)
    return scored

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
    print UPLOAD_FOLDER
    name = session.get('filename')
    print name
    rescore = session.get('rescore')
    path = UPLOAD_FOLDER + '/' + name
    print path
    # use try/except here since file is deleted immediatly after being processed
    # if user try's to reload it will redirect them to upload page
    if os.path.exists(path):
        try:
            print 'trying'
            scored_df = build_scored_df(path, rescore = rescore)
            print 'scored_df'
            save_name = 'scored_{}.csv'.format(name[:-5])
            saved_results = scored_df.to_csv(UPLOAD_FOLDER + '/' + save_name)
            session['scored_path'] = UPLOAD_FOLDER + '/' + save_name
            session['scored_filename'] = save_name
            os.remove(path)
            return render_template('results.html', name=name,
                                    f = scored_df.to_html())
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
    app.run()
