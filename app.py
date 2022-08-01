from boto3.session import Session
import json
import pandas as pd
import io
import numpy
import matplotlib.pyplot as plt
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os

mail_subject = os.environ['MAIL_SUBJECT']
mail_from = os.environ['MAIL_FROM']
mail_to = os.environ['MAIL_TO']
out_put_file = os.environ['OUT_PUT_FILE']

session = Session(region_name='ap-northeast-1')
dynamodb = session.resource('dynamodb')
mail_client = session.client('ses')

def handler(event, context):
    try:
        # get data and change format
        items = get_stock_monthly_data()
        csv_text = change_format(items)

        # analyzing
        df = get_data_frame(csv_text)
        df_target = get_data_frame_for_symbol(df, 'ALL')

        create_chart_graph(df_target)

        send_mail()
    except Exception as e:
        print(e)

"""
send mail
"""
def send_mail():
    msg = MIMEMultipart()

    msg['Subject'] = mail_subject
    msg['From'] = mail_from
    msg['To'] = mail_to
    # body = MIMEText('this is monthly profit.', 'plain')
    # msg.attach(body)

    if os.path.exists(out_put_file) == False:
        raise Exception("file not found.")

    att = MIMEApplication(open(out_put_file, 'rb').read())
    att.add_header('Content-Disposition','attachment',filename=os.path.basename(out_put_file))
    msg.attach(att)

    mail_client.send_raw_email(
        Destinations=[ mail_to ],
        RawMessage={
            'Data': msg.as_string(),
        },
        Source=mail_from,
    )

"""
create chart graph
"""
def create_chart_graph(df_target):
    """ 2軸グラフの作成 """
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()

    ax1.bar(df_target['date'], df_target['amount'], label='amount')
    ax2.plot(df_target['date'], df_target['profit'], marker='o', color='red', label='profit')

    ax1.legend(bbox_to_anchor=(0, 1), loc='upper left', borderaxespad=0.5, fontsize=10)
    ax2.legend(bbox_to_anchor=(0, 0.9), loc='upper left')

    ax1.set_ylabel('total amount')
    ax2.set_ylabel('profit/loss')

    fig.savefig(out_put_file)

"""
get data frame for symbol
"""
def get_data_frame_for_symbol(df, symbol='ALL') -> pd.DataFrame:
    df_target = df[df['symbol'] == symbol]
    return df_target.sort_values('date')

"""
get pandas data frame
"""
def get_data_frame(csv_text) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(csv_text), header=None, parse_dates=True)
    df.columns = ["date","symbol","amount","profit"]
    return df

"""
change format, json to csv file format
"""
def change_format(items) -> str:
    csv_text = ''
    for item in items:
        json_body = json.loads(item['body'])
        created_at = json_body['created_at']
        created_at = created_at[:7]

        all_amount = 0
        all_profit = 0
        for d in json_body['body']:
            symbol = d['symble']
            amount = d['bid'] * d['hold'] # 投資額
            profit = (d['value'] - d['bid']) * d['hold'] # 利益 (現在値-購入単価)*保有数
            csv_text += format("%s,%s,%.2f,%.2f\n" % (created_at, symbol, amount, profit))
            all_amount += amount
            all_profit += profit
        csv_text += format("%s,%s,%.2f,%.2f\n" % (created_at, 'ALL', all_amount, all_profit))
    return csv_text

"""
get stock monthly data from dynamodb
"""
def get_stock_monthly_data():
    table = dynamodb.Table('stock-monthly-data')
    result = table.scan()
    return result["Items"]

# if __name__ == '__main__':
#     handler(None, None)