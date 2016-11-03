from flask import Flask, flash, render_template, request, redirect, \
                  url_for, session, send_file
from flask.ext.session import Session
from werkzeug.utils import secure_filename
from score_code import ScoreSA
import tempfile
import os
import json

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
                UPLOAD_FOLDER = tempfile.mkdtemp()
                session['UPLOAD_FOLDER'] = UPLOAD_FOLDER
                session['filename'] = filename
                session['rescore'] = rescore

                print UPLOAD_FOLDER

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

    info = ScoreSA(filename = name, upload_folder = UPLOAD_FOLDER, rescore = rescore)

    # use try/except here since file is deleted immediatly after being processed
    # if user try's to reload it will redirect them to upload page
    if os.path.exists(info.path):
        try:
            info.save_scored()
            session['scored_path'] = info.scored_save_path
            session['scored_filename'] = info.scored_save_name
            os.remove(info.path)
            if info.has_groups:
                info.save_descriptive()
                session['described_path'] = info.descriptive_save_path
                session['described_filename'] = info.descriptive_save_name
                return render_template('results.html', name=name,
                                       f = info.scored_df.to_html(),
                                       f1 = info.descriptive.to_html(),
                                       describe = info.has_groups)
            else:
                return render_template('results.html', name=name,
                                       f = info.scored_df.to_html(),
                                       describe = info.has_groups)
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
    if request.method == 'POST':
        if request.form['submit'] == 'download scored csv':
            scored_path = session.get('scored_path')
            scored_name = session.get('scored_filename')
            return send_file(scored_path,
                             as_attachment = True,
                             attachment_filename=scored_name)
        if request.form['submit'] == 'download descriptive csv':
            descr_path = session.get('described_path')
            descr_name = session.get('described_filename')
            return send_file(descr_path,
                             as_attachment = True,
                             attachment_filename = descr_name)




if __name__ == '__main__':
    sess.init_app(app)
    app.run(debug = True)
