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

ALLOWED_EXTENSIONS = set(['xlsx', 'xlsm', 'xlt'])

app = Flask(__name__)
sess = Session()

def allowed_file(filename):
    # checks to see if an uploaded file is of proper filetype
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def build_scored_df(filename, rescore=None):
    # builds the scored dataframe
    df = pd.read_excel(filename, index_col = 0, header = 0)
    if df['pre_weight'].empty == False and \
       df['post_weight'].empty == False:
        weight_percentage = df['post_weight'] / df['pre_weight']
        weight_percentage.name = 'weight_percentage'

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
                print 'saving file'
                UPLOAD_FOLDER = tempfile.mkdtemp()
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
    try:
        scored_df = build_scored_df(path, rescore = rescore)
        save_name = 'scored_{}.csv'.format(name[:-5])
        saved_results = scored_df.to_csv(UPLOAD_FOLDER + '/' + save_name)
        session['scored_path'] = UPLOAD_FOLDER + '/' + save_name
        session['scored_filename'] = save_name
        os.remove(path)
        return render_template('results.html', name=name,
                               f = scored_df.to_html())
    except:
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
    app.secret_key = os.environ['SA_SK']
    app.config['SESSION_TYPE'] = 'filesystem'

    sess.init_app(app)

    app.run()
