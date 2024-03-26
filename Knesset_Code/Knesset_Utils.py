import copy
import urllib
import pickle
import dill
from operator import add
import urllib.request
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
from docx import Document
import numpy as np
import pandas as pd
import os
from bs4 import BeautifulSoup
from datetime import datetime, date
import datetime as dt
import re
import os.path
import win32com.client
from transformers import AutoTokenizer, AutoModel, pipeline


# All static functions
def aggregate_sentiments(knessets_sentiment_list):
    for k in knessets_sentiment_list:
        for c in k.committees:
            for m in c.committee_meetings:
                for participant, sentiments in m.participants_sentiments.items():
                    participant_num_of_sayings = len(m.participants_sayings[participant])
                    if participant_num_of_sayings > 0:
                        m.participants_sentiments[participant]['neutral'] /= participant_num_of_sayings
                        m.participants_sentiments[participant]['positive'] /= participant_num_of_sayings
                        m.participants_sentiments[participant]['negative'] /= participant_num_of_sayings
    return knessets_sentiment_list


def translate_all(knessets_trans_list):
    pipe = pipeline("translation", model="Helsinki-NLP/opus-mt-tc-big-he-en")
    for k in knessets_trans_list:
        for c in k.committees:
            for m in c.committee_meetings:
                m.participants_sayings_english = {}
                for participant, saying in m.participants_sayings.items():
                    m.participants_sayings_english[participant] = pipe(saying)
            print(f'Finished Translating Committee {c.committee_name} in Knesset {k.knesset_number}')
        print(f'Finished Translating Knesset {k.knesset_number}')
    return knessets_trans_list


def save_object(obj, filename):
    with open(filename, 'wb') as outp:  # Overwrites any existing file.
        pickle.dump(obj, outp, pickle.HIGHEST_PROTOCOL)


def load_object(filename):
    with open(filename, 'rb') as inp:
        file = pickle.load(inp)
    return file


def convert_word_doc_to_docx(folder_path):
    baseDir = folder_path  # Starting directory for directory walk
    word = win32com.client.Dispatch("Word.application")

    for dir_path, dirs, files in os.walk(baseDir):
        for file_name in files:
            file_path = os.path.join(dir_path, file_name)
            file_name, file_extension = os.path.splitext(file_path)
            if "~$" not in file_name:
                if file_extension.lower() == '.doc':  #
                    docx_file = '{0}{1}'.format(file_path, 'x')
                    if not os.path.isfile(docx_file):  # Skip conversion where docx file already exists
                        file_path = os.path.abspath(file_path)
                        docx_file = os.path.abspath(docx_file)
                        try:
                            wordDoc = word.Documents.Open(file_path)
                            wordDoc.SaveAs2(docx_file, FileFormat=16)
                            wordDoc.Close()
                            os.unlink(file_path)
                        except Exception as e:
                            print('Failed to Convert: {0}'.format(file_path))
                            print(e)
                    else:
                        try:
                            file_path = os.path.abspath(file_path)
                            os.unlink(file_path)
                        except:
                            continue


def convert_month_to_num(text_date):
    date_dict = {'בינואר': 1, 'בפברואר': 2, 'במרץ': 3, 'במרס': 3, 'באפריל': 4, 'במאי': 5, 'ביוני': 6,
                 'ביולי': 7, 'באוגוסט': 8, 'בספטמבר': 9, 'באוקטובר': 10, 'בנובמבר': 11, 'בדצמבר': 12}
    return int(date_dict[text_date])


def substring_index(the_list, substring):
    for i, s in enumerate(the_list):
        if substring in s:
            return i
    return 10000000 * 10000000


def get_statement_frequency_by_time(k_list, search_statement):
    # Summarize the number of 'search_statement' occurrences by date and by knesset number + committee
    statements = []
    # Loop through the knessets
    for knesset in k_list:
        # Loop through the committees in the current knesset
        for comm in knesset.committees:
            # Loop through the meetings of the current committee
            for meeting in comm.committee_meetings:
                # If there is a valid date to the meeting save all sayings
                if meeting.date:
                    try:
                        protocol_num = meeting.protocol_numnber
                    except:
                        protocol_num = -1
                    # Save all statements by their knesset number, committee and date
                    statements.append({'knesset_num': knesset.knesset_number, 'com_name': comm.committee_name,
                                       'protocol_num': protocol_num, 'date': meeting.date, 'sayings': meeting.all_text})

    # Sum number of occurrences of 'search statement' in each meeting
    summary = pd.DataFrame(columns=['Knesset_Num', 'Committee_Name', 'Protocol_Num', 'Date', 'Num_Of_Occurrences'])
    for statement in statements:
        summary = pd.concat([summary, pd.DataFrame(data=np.array([statement['knesset_num'], statement['com_name'],
                                                                  statement['protocol_num'], statement['date'],
                                                                  sum(search_statement in s for s in
                                                                      statement['sayings'])]).reshape(1, -1),
                                                   columns=summary.columns)])

    # Summarize number of occurrences by date
    summary_by_date = summary[['Date', 'Num_Of_Occurrences']]
    summary_by_date = summary_by_date.groupby(['Date']).sum()

    # Summarize number of occurrences by knesset number and committee
    summary_by_committee = summary[['Knesset_Num', 'Committee_Name', 'Num_Of_Occurrences']]
    summary_by_committee = summary_by_committee.groupby(['Knesset_Num', 'Committee_Name']).sum()

    # Plot the statement occurrences by date
    plt.figure(figsize=[16, 6])
    plt.plot(summary_by_date)
    plt.xlabel('Date', fontsize=14)
    plt.ylabel('Num Of Occurrences', fontsize=14)
    plt.title(f'{search_statement[::-1]} Occurrences By Date', fontsize=16)
    plt.grid()
    plt.show()

    return summary, summary_by_date, summary_by_committee


def create_sentiment_df(knessets):
    cols = ['Knesset_Num', 'Committee_Name', 'Committee_Protocol_Num', 'Date', 'Member_Name', 'Speaking_Times', 'Avg_Neutral', 'Avg_Positive', 'Avg_Negative']
    df = pd.DataFrame(columns=cols)
    for k in knessets:
        knesset_num = k.knesset_number
        for c in k.committees:
            com_name = c.committee_name
            for m in c.committee_meetings:
                protocol_num = m.protocol_number
                date = m.date
                for participant, sayings in m.participants_sayings.items():
                    member_name = participant
                    speak_times = len(m.participants_sayings[participant])
                    neutral = m.participants_sentiments[participant]['neutral']
                    positive = m.participants_sentiments[participant]['positive']
                    negative = m.participants_sentiments[participant]['negative']

                    row = np.array([knesset_num, com_name, protocol_num, date, member_name, speak_times, neutral, positive, negative]).reshape(1, -1)
                    df = pd.concat([df, pd.DataFrame(row, columns=cols)])
    return df


# ----------------------------------------------- Processing Functions ----------------------------------------------- #

def create_folders_knessets_and_committees(path, url_k):
    # Create folders for all knessets and all committees
    committees = {}
    knesset_nums = []

    for i in range(1, 26):
        flag = True
        # Knesset folders
        knesset_path = path + '/Knesset_' + str(i)
        if not os.path.exists(knesset_path):
            os.makedirs(knesset_path)

        url_knesset = url_k + str(i)
        with urllib.request.urlopen(url_knesset) as response:
            xml_data = response.read()

        # While there's a next page available
        while flag:
            flag = False
            root = ET.fromstring(xml_data)
            entries = root.findall('{http://www.w3.org/2005/Atom}entry')
            try:
                next_link = root[104].get('href')
                print(next_link)
                flag = True
            except:
                print("No more committees for knesset:", i)

            for ind, entry in enumerate(entries):
                content = entry.find('{http://www.w3.org/2005/Atom}content')
                committee_id = content[0][0].text
                committee_name = content[0][1].text
                knesset_num = content[0][4].text

                committee_name = committee_name.replace('"', "")
                committee_name = committee_name.replace(':', "")
                committee_name = committee_name.lstrip()
                committee_name = committee_name.rstrip()
                committees[committee_id] = committee_name
                knesset_nums.append(knesset_num)

                # Add a folder for each committee
                committee_path = knesset_path + '/' + str(committee_name)
                if not os.path.exists(committee_path):
                    os.makedirs(committee_path)

            # Get the next page if one exists
            if flag:
                with urllib.request.urlopen(next_link) as response:
                    xml_data = response.read()


def process_all_protocols(path, knessets_list, error_save_flag=False):
    # Process all the protocols in the knessets list
    error_df = pd.DataFrame(columns=['Knesset Num', 'Knesset Committee', 'Num Error Protocols', 'Total Num Protocols'])
    for knesset in knessets_list[-5:]:
        for ind, com in enumerate(knesset.committees):
            error_df = knesset.committees[ind].process_protocols(knesset, com, error_df)
        if error_save_flag:
            error_df.to_csv(path + '/Protocols_Errors_Summary.csv', index=False, encoding='utf-8-sig')
        knesset.summarize_committees_length_and_amount()
        knesset.get_committees_structure_by_parties()
    return knessets_list



