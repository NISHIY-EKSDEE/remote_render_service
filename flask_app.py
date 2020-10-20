from flask import Flask, render_template, request, Markup
from werkzeug.utils import secure_filename
import os, requests, zipfile, time
import jenkins
import urllib.parse

UPLOAD_FOLDER = 'uploads'
server = jenkins.Jenkins('http://localhost:8080', username='username', password='password')
token = 'token'

app = Flask(__name__, static_folder='static')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/api/remote_render', methods=['POST'])
def remote_render_api():

    job_name = 'render_from_zip'
    file = request.files['source_file']
    filename = secure_filename(file.filename)
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(path)
    file_path = os.path.abspath(path)
    
    next_number = server.get_job_info(job_name)['nextBuildNumber']
    server.build_job(job_name, fill_the_data(request, file_path), token=token)
    
    return render_template("result_table_row.html", number=next_number)

@app.route('/api/check_build/<job_name>/<int:number>', methods=['POST'])
def check_build(job_name, number):
    info = server.get_build_info(job_name, number)

    if info["building"]:
        return "Building"

    if info["result"] != "SUCCESS":
        return info["result"]

    return "SUCCESS"

@app.route('/api/get_artifacts/<job_name>/<int:number>', methods=['POST'])
def get_artifacts(job_name, number):
    img_block = ""
    info = server.get_build_info(job_name, number)
    if info["result"] == "SUCCESS":
        for artifact in info["artifacts"]:
            if artifact["fileName"].endswith('.png') or artifact["fileName"].endswith('.bmp') or artifact["fileName"].endswith('.jpg'):
                save_dir = os.path.join("static", str(number))
                if not os.path.exists(save_dir):
                    os.mkdir(save_dir)
                filename = os.path.join(save_dir, artifact["fileName"])
                url_rel_path = urllib.parse.quote(artifact["relativePath"])
                url = f"http://localhost:8080/job/render_from_zip/{number}/artifact/{url_rel_path}"
                downloadFile(url, filename)
                img_block += f'<p><img src="{filename}"></p>'
    return render_template("result_block.html", image_block=Markup(img_block))
                



def fill_the_data(request, zip_path):
    data = {"source_path" : zip_path, "delay": "0sec"}
    if request.form["width"]:
        data["width"] = request.form["width"]
    if request.form["height"]:
        data["height"] = request.form["height"]
    if request.form["min_samples"]:
        data["min_samples"] = request.form["min_samples"]
    if request.form["max_samples"]:
        data["max_samples"] = request.form["max_samples"]
    if request.form["noise_threshold"]:
        data["noise_threshold"] = request.form["noise_threshold"]
    if request.form["file_format"]:
        data["file_format"] = request.form["file_format"]
    if request.form["time_limit"]:
        data["time_limit"] = request.form["time_limit"]
    if request.form["labels"]:
        data["labels"] = request.form["labels"]
    return data

def downloadFile(url, filename):
    r = requests.get(url)
    with open(filename, 'wb') as f:
        f.write(r.content)
    