from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pandas as pd
from sqlalchemy import create_engine, text
import os

app = Flask(__name__)
app.secret_key = "super_secure_key"

UPLOAD_FOLDER = '/shared_data'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

engine = create_engine("postgresql+psycopg2://user:password@db:5432/sportsdb")

@app.route('/', methods=['GET', 'POST'])
def index():
    table_data = None
    table_name = None
    error = None
    query = None
    results = None
    columns = []

    if request.method == 'POST':
        file = request.files.get('csv_file')
        if file and file.filename.endswith('.csv'):
            table_name = os.path.splitext(file.filename)[0].replace(" ", "_")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)

            try:
                df = pd.read_csv(file_path)
                df.to_sql(table_name, engine, if_exists='replace', index=False)

                session['table_name'] = table_name
                session['row_count'] = df.shape[0]
                session['col_count'] = df.shape[1]
                session['dtypes'] = df.dtypes.astype(str).to_dict()
                session['null_counts'] = df.isna().sum().to_dict()
                session['unique_info'] = {col: df[col].nunique() for col in df.columns}
                session['columns'] = df.columns.tolist()

                table_data = df.head(20).to_html(classes='table table-striped', index=False)

            except Exception as e:
                error = str(e)

    return render_template(
        'index.html',
        table_data=table_data,
        table_name=session.get('table_name'),
        row_count=session.get('row_count'),
        col_count=session.get('col_count'),
        dtypes=session.get('dtypes', {}),
        null_counts=session.get('null_counts', {}),
        unique_info=session.get('unique_info', {}),
        query=query,
        query_results=results,
        columns=session.get('columns', []),
        error=error
    )

@app.route('/query', methods=['POST'])
def run_query():
    query = request.form.get('sql_query')
    error = None
    results = None
    columns = []

    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            results = result.fetchall()
            columns = result.keys()
    except Exception as e:
        error = str(e)
        results = []
        columns = []

    return render_template(
        'index.html',
        table_data=None,
        table_name=session.get('table_name'),
        row_count=session.get('row_count'),
        col_count=session.get('col_count'),
        dtypes=session.get('dtypes', {}),
        null_counts=session.get('null_counts', {}),
        unique_info=session.get('unique_info', {}),
        query=query,
        query_results=results,
        columns=columns,
        error=error
    )

@app.route('/drop_empty_columns', methods=['POST'])
def drop_empty_columns():
    table_name = session.get('table_name')
    if not table_name:
        flash("No table loaded to clean.", "danger")
        return redirect(url_for('index'))

    try:
        df = pd.read_sql_table(table_name, engine)
        df_cleaned = df.dropna(axis=1, how='all')
        df_cleaned.to_sql(table_name, engine, if_exists='replace', index=False)

        session['row_count'] = df_cleaned.shape[0]
        session['col_count'] = df_cleaned.shape[1]
        session['dtypes'] = df_cleaned.dtypes.astype(str).to_dict()
        session['null_counts'] = df_cleaned.isna().sum().to_dict()
        session['unique_info'] = {col: df_cleaned[col].nunique() for col in df_cleaned.columns}
        session['columns'] = df_cleaned.columns.tolist()

        flash("✅ Empty columns dropped and table updated.", "success")
    except Exception as e:
        flash(str(e), "danger")

    return redirect(url_for('index'))

@app.route('/download/<format>')
def download_data(format):
    table_name = session.get('table_name')
    if not table_name:
        return "No data loaded", 400

    df = pd.read_sql_table(table_name, engine)

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{table_name}.{format}")
    if format == 'csv':
        df.to_csv(file_path, index=False)
    elif format == 'parquet':
        df.to_parquet(file_path, index=False)
    elif format == 'txt':
        df.to_csv(file_path, sep='\t', index=False)
    else:
        return "Unsupported format", 400

    return jsonify({"message": "File created.", "path": file_path})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
