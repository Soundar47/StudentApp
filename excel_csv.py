import pandas as pd

file = r"E:\vs\flask_project\StudentApp\I M.Sc Biodata Template.xls"

try:
    df = pd.read_excel(file, engine="xlrd")
    print(df.head())
    print(df.columns)
except Exception as e:
    print(e)