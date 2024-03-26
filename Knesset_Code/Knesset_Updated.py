from Knesset_Utils import *


def populate_all_knessets_from_ready_files(path, committee_url, member_url, save_flag=False):
    # Populate all knessets from ready files
    knessets_list = []
    parties_df = pd.read_csv(path + '/All_Parties.csv')
    members_df = pd.read_csv(path + '/All_Knesset_Members.csv')
    # all_parties_df = pd.DataFrame(columns=['Knesset_num', 'Party_ID', 'Party_name', 'Start_date', 'Finish_date'])
    # all_members_df = pd.DataFrame(
    #     columns=['Knesset Number', 'Member ID', 'First Name', 'Last Name', 'Gender', 'Party ID', 'Party Name',
    #              'Role ID', 'Role Desc'])

    for k in range(15, 26):
        save_path = path + '/Knesset_' + str(k)
        # Populate and append current knesset
        knesset = Knesset(save_path, k)
        knesset.populate_knesset_from_file(save_path, parties_df, members_df)
        knessets_list.append(knesset)
        print("Finished populating knesset", str(k))
        if save_flag:
            save_object(knesset, path + '/knesset_' + str(k) + '_object.pkl')
    return knessets_list


# All class objects
class Knesset:
    def __init__(self, save_path, knesset_number):
        self.save_path = save_path
        self.knesset_number = knesset_number
        self.knesset_members = []
        self.parties = []
        self.committees = []
        self.melia_meetings = []
        self.committees_summary = pd.DataFrame(columns=['Committee Name', 'Num of Meetings', 'Avg Meeting Length'])

    class KnessetMember:

        def __init__(self, person_id, first_name, last_name, gender, role_id, role_desc):
            self.person_id = person_id
            self.first_name = first_name
            self.last_name = last_name
            self.gender_id = gender
            self.role_id = role_id
            self.role_desc = role_desc
            self.speaking_frequency_by_date = {}

    class Party:

        def __init__(self, id, name, s_date, f_date):
            self.party_id = id
            self.party_name = name
            self.party_start_date = s_date
            self.party_finish_date = f_date
            self.party_members = []
            self.in_coalition = None

    class Committee:

        def __init__(self, name, protocols):
            self.committee_name = name
            self.committee_members_by_parties = {}
            self.num_of_members_per_party = {}
            self.committee_parties_words_and_sentences_count = {}  # 1st number is words count, 2nd is sentences and 3rd num of speaking times
            self.committee_participants_words_and_sentences_count = {}  # 1st number is words count, 2nd is sentences and 3rd num of speaking times
            self.committee_protocols = protocols
            self.committee_meetings = []
            self.chairman = ''
            self.committee_avg_meeting_length = -1
            self.num_of_committee_meetings = -1

        class CommitteeMeeting:

            def __init__(self, doc):
                super().__init__()
                self.meeting_document = doc
                self.committee = ''  # Which committee held the meeting
                self.protocol_number = 0
                self.subject = ''
                self.date = ''
                self.meeting_length = 0  # Length of the meeting
                self.chairman = ''
                self.participants_parties = {}  # All participants and the parties they belong to
                self.parties_words_and_sentences_count = {}  # 1st number is words count, 2nd is sentences and 3rd num of speaking times
                self.participants_sayings = {}  # All sayings in hebrew in the meeting of every participant
                self.participants_sayings_english = {}  # All sayings in english in the meeting of every participant
                self.participants_sentiments = {}
                self.participants_words_and_sentences_count = {}  # 1st number is words count, 2nd is sentences and 3rd num of speaking times
                self.all_text = []  # All sayings in the meeting

            def process_meeting_file(self, com, knesset):
                # pipe = pipeline("translation", model="Helsinki-NLP/opus-mt-tc-big-he-en")

                sentiment_analysis = pipeline(
                    "sentiment-analysis",
                    model="avichr/heBERT_sentiment_analysis",
                    tokenizer="avichr/heBERT_sentiment_analysis",
                    top_k=None
                )

                # if knesset.knesset_number > 21:

                # else:

                self.committee = com
                # Go through all paragraphs in the document
                for p in self.meeting_document.paragraphs:
                    if len(p.text) > 0:
                        text = p.text.strip('\n')
                        text = text.strip('\t')
                        # Save all separated text
                        self.all_text.append(text)

                    # Save 'dry' data about the meeting
                    if len(p.runs) > 0:
                        if 'פרוטוקול מס' in p.runs[0].text:
                            try:
                                self.protocol_number = int(''.join([char for char in p.runs[1].text if char.isdigit()]))
                            except:
                                temp = p.runs[0].text
                                temp = temp.split(' ')
                                temp = temp[len(temp) - 1]
                                if ',' in temp:
                                    temp = temp[-1]
                                try:
                                    self.protocol_number = int(temp)
                                except:
                                    try:
                                        self.protocol_number = int(p.runs[2].text)
                                    except:
                                        print("Error in protocol number")
                        elif '<< נושא >>' in p.runs[0].text:
                            try:
                                self.subject = p.runs[1].text
                            except:
                                try:
                                    self.subject = re.sub("<< נושא >>", '', p.runs[0].text)
                                    self.subject = self.subject.strip()
                                except:
                                    print(
                                        f"Error with the committee subject. knesset number: {knesset.knesset_number}, committee: {self.committee.committee_name}, in protocol number: {self.protocol_number}")

                # Calculate meeting date
                try:
                    date = self.all_text[min(max(substring_index(self.all_text, 'סדר היום:'), 0),
                                             substring_index(self.all_text, 'סדר היום')) - 1]
                    start_time = self.all_text[min(max(substring_index(self.all_text, 'סדר היום:'), 0),
                                                   substring_index(self.all_text, 'סדר היום')) - 1][-5:]
                    if date == ' ' or date == '':
                        date = self.all_text[substring_index(self.all_text, 'סדר היום') - 2]
                        start_time = self.all_text[substring_index(self.all_text, 'סדר היום') - 2][-5:]
                except:
                    date = self.all_text[substring_index(self.all_text, 'סדר-היום') - 1]
                    start_time = self.all_text[substring_index(self.all_text, 'סדר-היום') - 1][-5:]
                    if date == ' ' or date == '':
                        date = self.all_text[substring_index(self.all_text, 'סדר-היום') - 2]
                        start_time = self.all_text[substring_index(self.all_text, 'סדר-היום') - 2][-5:]
                try:
                    date = date[date.rfind("(") + 1: date.rfind(")")].split()
                    self.date = dt.date(int(date[2]), convert_month_to_num(date[1]), int(date[0]))
                except:
                    print(
                        f"Error with meeting date. knesset number: {knesset.knesset_number}, committee: {self.committee.committee_name}, in protocol number: {self.protocol_number}")

                # Save the committee members
                start = substring_index(self.all_text, 'חברי הוועדה:')
                havrei = substring_index(self.all_text, 'חברי הכנסת:')
                muzmanim = substring_index(self.all_text, 'מוזמנים:')
                mishpati = substring_index(self.all_text, 'ייעוץ משפטי:')
                menahel = substring_index(self.all_text, 'מנהל הוועדה:')
                if havrei < 10000000 * 100000:
                    end_list = [muzmanim, mishpati, menahel]
                    end = [x for x in end_list if x > havrei]
                    end = min(end) if len(end) > 0 else havrei + 10
                else:
                    end = min(muzmanim, mishpati, menahel)
                for member in self.all_text[start + 1: end]:
                    if 'יו"ר' in member:
                        if member.find('–') >= 0:
                            member = member[:member.find('–')]
                        if member.find(' -') >= 0:
                            member = member[:member.find(' -')]
                        if member.find(' (') >= 0:
                            member = member[:member.find(' (')]
                        member = re.sub('<< יור >>', '', member)
                        member = re.sub('היו"ר', '', member)
                        member = re.sub(':', '', member)
                        member = re.sub("פרופ' ", '', member)
                        member = re.sub('-', ' ', member)
                        member = re.sub('מ"מ', ' ', member)
                        member = member.strip()
                        self.chairman = member

                    for party in knesset.parties:
                        for mem in party.party_members:
                            if mem.first_name + ' ' + mem.last_name == member:
                                self.participants_sayings[member] = list()
                                self.participants_sentiments[member] = {'neutral': 0, 'positive': 0, 'negative': 0}
                                self.participants_sayings_english[member] = list()
                                self.participants_parties[member] = party.party_name

                # Get meeting length
                try:
                    if start_time[0] == ' ' or start_time[len(start_time) - 1] == ' ':
                        start_time = '0' + start_time[1:]
                        start_time = start_time.strip(' ')
                    try:
                        end_time = self.all_text[substring_index(self.all_text, 'הישיבה ננעלה בשעה')]
                        end_time = end_time.strip('<< סיום >>')
                        end_time = end_time.strip('הישיבה ננעלה בשעה')
                    except:
                        end_time = self.all_text[substring_index(self.all_text, 'הפרוטוקול הסתיים בשעה')]
                        end_time = end_time.strip('<< סיום >>')
                        end_time = end_time.strip('הפרוטוקול הסתיים בשעה')
                    end_time = end_time.strip(' ')
                    end_time = end_time.strip('.')
                    t1 = datetime.strptime(start_time, "%H:%M")
                    if end_time[:2] == '24':
                        end_time = '00' + end_time[2:]
                    t2 = datetime.strptime(end_time, "%H:%M")
                    self.meeting_length = (t2 - t1).total_seconds() / 3600
                except:
                    print(
                        f"Error with meeting time. knesset number: {knesset.knesset_number}, committee: {self.committee.committee_name}, in protocol number: {self.protocol_number}")

                # Save all members' sayings
                for ind, statement in enumerate(self.all_text):
                    if '<< יור >>' in statement:
                        speaker = self.chairman
                        if speaker in self.participants_sayings.keys():
                            self.participants_sayings[speaker].append(self.all_text[ind + 1])
                            try:
                                self.participants_sentiments[speaker]['neutral'] += sentiment_analysis(self.all_text[ind + 1])[0][0]['score']
                                self.participants_sentiments[speaker]['positive'] += sentiment_analysis(self.all_text[ind + 1])[0][1]['score']
                                self.participants_sentiments[speaker]['negative'] += sentiment_analysis(self.all_text[ind + 1])[0][2]['score']
                            except:
                                print(f'Error in sentiment analysis of saying: {self.all_text[ind + 1]}, in Knesset {knesset.knesset_number}, Committee {com.committee_name}')

                            # self.participants_sayings_english[speaker].append(pipe(self.all_text[ind + 1]))

                    elif '<< דובר >>' in statement:
                        speaker = statement.strip('<< דובר >>')
                        speaker = "".join(re.split("\(|\)", speaker)[::2])
                        speaker = speaker.strip(' :')
                        if speaker in self.participants_sayings.keys():
                            self.participants_sayings[speaker].append(self.all_text[ind + 1])
                            try:
                                self.participants_sentiments[speaker]['neutral'] += sentiment_analysis(self.all_text[ind + 1])[0][0]['score']
                                self.participants_sentiments[speaker]['positive'] += sentiment_analysis(self.all_text[ind + 1])[0][1]['score']
                                self.participants_sentiments[speaker]['negative'] += sentiment_analysis(self.all_text[ind + 1])[0][2]['score']
                            except:
                                print(
                                    f'Error in sentiment analysis of saying: {self.all_text[ind + 1]}, in Knesset {knesset.knesset_number}, Committee {com.committee_name}')
                            # self.participants_sayings_english[speaker].append(pipe(self.all_text[ind + 1]))

                # Sum number of words, number of sentences and number of speaking times of each member and each party
                for participant, party in self.participants_parties.items():
                    sayings_united = ' '.join(self.participants_sayings[participant])
                    num_of_words = len(sayings_united.split(' '))
                    num_of_sentences = len(sayings_united.split('.'))
                    num_of_speaking_times = len(self.participants_sayings[participant])
                    if participant not in self.participants_words_and_sentences_count.keys():
                        self.participants_words_and_sentences_count[participant] = [0, 0, 0]
                        self.parties_words_and_sentences_count[party] = [0, 0, 0]
                    self.participants_words_and_sentences_count[participant] = list(
                        map(add, self.participants_words_and_sentences_count[participant],
                            [num_of_words, num_of_sentences, num_of_speaking_times]))
                    self.parties_words_and_sentences_count[party] = list(
                        map(add, self.parties_words_and_sentences_count[party],
                            [num_of_words, num_of_sentences, num_of_speaking_times]))

        def summarize_committee_words_and_sentences_count(self):
            # Sum number of words, number of sentences and number of speaking times
            # of each member and each party through all the committee meetings
            for meeting in self.committee_meetings:
                for participant, party in meeting.participants_parties.items():
                    if participant not in self.committee_participants_words_and_sentences_count.keys():
                        self.committee_participants_words_and_sentences_count[participant] = [0, 0, 0]
                        self.committee_parties_words_and_sentences_count[party] = [0, 0, 0]
                    num_of_words = meeting.participants_words_and_sentences_count[participant][0]
                    num_of_sentences = meeting.participants_words_and_sentences_count[participant][1]
                    num_of_speaking_times = meeting.participants_words_and_sentences_count[participant][2]
                    self.committee_participants_words_and_sentences_count[participant] = list(
                        map(add, self.committee_participants_words_and_sentences_count[participant],
                            [num_of_words, num_of_sentences, num_of_speaking_times]))
                    self.committee_parties_words_and_sentences_count[party] = list(
                        map(add, self.committee_parties_words_and_sentences_count[party],
                            [num_of_words, num_of_sentences, num_of_speaking_times]))

        def plot_speaking_frequency_in_committee(self, participants, percentage):
            if participants:
                frequency_dict = copy.deepcopy(self.committee_participants_words_and_sentences_count)
                title = 'Participants'
            else:
                frequency_dict = copy.deepcopy(self.committee_parties_words_and_sentences_count)
                title = 'Parties'

            dict_words, dict_sentences, dict_speaking_times = {}, {}, {}

            # Iterate over the original dictionary
            for key, value in frequency_dict.items():
                words, sentences, speaking_times = value

                # Update the respective sorted dictionary
                dict_words[key] = words
                dict_sentences[key] = sentences
                dict_speaking_times[key] = speaking_times

            # Sort the dictionaries by their values
            sorted_dict_words = {k: v for k, v in sorted(dict_words.items(), key=lambda item: item[1], reverse=True)}
            sorted_dict_sentences = {k: v for k, v in
                                     sorted(dict_sentences.items(), key=lambda item: item[1], reverse=True)}
            sorted_dict_speaking_times = {k: v for k, v in
                                          sorted(dict_speaking_times.items(), key=lambda item: item[1], reverse=True)}

            def absolute_value(val):
                a = np.round(val / 100. * sum(original_vals), 0)
                return a

            if percentage:
                display = '%1.1f%%'
            else:
                display = absolute_value

            plt.figure(figsize=(18, 6))
            plt.subplot(131)
            original_vals = list(sorted_dict_words.values())
            plt.pie(list(sorted_dict_words.values()), labels=[l[::-1] for l in list(sorted_dict_words.keys())],
                    autopct=display)
            plt.title(f'{title} Words Frequency')
            plt.subplot(132)
            original_vals = list(sorted_dict_sentences.values())
            plt.pie(list(sorted_dict_sentences.values()), labels=[l[::-1] for l in list(sorted_dict_sentences.keys())],
                    autopct=display)
            plt.title(f'{title} Sentences Frequency')
            plt.subplot(133)
            original_vals = list(sorted_dict_speaking_times.values())
            plt.pie(list(sorted_dict_speaking_times.values()),
                    labels=[l[::-1] for l in list(sorted_dict_speaking_times.keys())], autopct=display)
            plt.title(f'{title} Speaking Times Frequency')
            plt.suptitle(f'Committee: {self.committee_name[::-1]}')
            plt.show()

        def plot_parties_representation_in_committee(self):
            sorted_data = sorted(self.num_of_members_per_party.items(), key=lambda x: x[1], reverse=True)
            parties_list = [l[0][::-1] for l in sorted_data]
            num_of_members_list = [n[1] for n in sorted_data]

            def absolute_value(val):
                a = np.round(val / 100. * sum(num_of_members_list), 0)
                return a

            plt.figure(figsize=(20, 7))
            plt.subplot(121)
            plt.pie(num_of_members_list, labels=parties_list, autopct=absolute_value)
            plt.title("Number Of Members In The Committee Per Party")
            plt.subplot(122)
            plt.pie(num_of_members_list, labels=parties_list, autopct='%1.1f%%')
            plt.title("Percent Of Members In The Committee Per Party")
            plt.show()

        def process_protocols(self, knesset, com, error_df):
            doc_counter = 0
            counter_error = 0
            for protocol_path in self.committee_protocols:
                convert_word_doc_to_docx(protocol_path)
                try:
                    protocol = Document(protocol_path)
                    committee_meeting = self.CommitteeMeeting(protocol)
                    committee_meeting.process_meeting_file(com, knesset)
                    committee_meeting.meeting_document = "Processed"
                    self.committee_meetings.append(committee_meeting)
                except Exception as e:
                    print("Error with protocol document in knesset: ", str(knesset.knesset_number), "committee: ",
                          str(com.committee_name))
                    print("Error", e)
                    counter_error += 1
                doc_counter += 1

            self.num_of_committee_meetings = len(self.committee_protocols)
            self.summarize_committee_words_and_sentences_count()
            error_df = error_df.append({'Knesset Num': knesset.knesset_number, 'Knesset Committee': com.committee_name,
                                        'Num Error Protocols': counter_error, 'Total Num Protocols': doc_counter},
                                       ignore_index=True)
            print("Finished processing protocols of committee:", str(com.committee_name), "in knesset:",
                  str(knesset.knesset_number))
            return error_df

    class MeliaMeeting:

        def __init__(self, doc):
            self.meeting_document = doc
            self.subject = ''
            self.date = ''
            self.length = 0  # Length of the meeting
            self.participants_parties = {}  # All participants and the parties they belong to
            self.chairman = ''
            self.all_text = []  # All sayings in the meeting
            self.participants_sayings = {}  # All sayings in the meeting of every participant

    def get_all_parties(self, url):
        flag = True
        parties_df = pd.DataFrame(columns=['Knesset_num', 'Party_ID', 'Party_name', 'Start_date', 'Finish_date'])
        index = -1
        # While there's a next page available
        while flag:
            flag = False
            with urllib.request.urlopen(url) as response:
                xml_data = response.read()
            root = ET.fromstring(xml_data)
            entries = root.findall('{http://www.w3.org/2005/Atom}entry')
            try:
                url = root[104].get('href')
                flag = True
            except:
                print("No more parties in knesset:", self.knesset_number)

            for ind, entry in enumerate(entries):
                index += 1
                content = entry.find('{http://www.w3.org/2005/Atom}content')
                party_id = content[0][0].text
                party_name = content[0][1].text
                if 'בראשות' in party_name:
                    party_name = party_name[:party_name.find('בראשות')]
                party_name = party_name.strip()
                if party_name[len(party_name) - 1] == '-':
                    party_name = party_name[:-1]
                    party_name = party_name.strip()
                s_date = content[0][3].text
                s_date = s_date[:10].split('-')
                s_date = dt.date(int(s_date[0]), int(s_date[1]), int(s_date[2]))
                f_date = content[0][4].text
                # If the party is not currently active
                if content[0][5].text == 'false':
                    f_date = f_date[:10].split('-')
                    f_date = dt.date(int(f_date[0]), int(f_date[1]), int(f_date[2]))
                party = self.Party(party_id, party_name, s_date, f_date)
                self.parties.append(party)
                parties_df.loc[index] = [self.knesset_number, party_id, party_name, s_date, f_date]

        parties_df.to_csv(self.save_path + '/Parties_Knesset_' + str(self.knesset_number) + '.csv',
                          encoding='utf-8-sig')
        return parties_df

    def get_all_knesset_members(self, url):
        members_df = pd.DataFrame(
            columns=['Knesset Number', 'Member ID', 'First Name', 'Last Name', 'Gender', 'Party ID', 'Party Name',
                     'Role ID', 'Role Desc'])
        idx = -1
        flag = True
        # While there's a next page available
        while flag:
            flag = False
            with urllib.request.urlopen(url) as response:
                xml_data = response.read()
            root = ET.fromstring(xml_data)
            entries = root.findall('{http://www.w3.org/2005/Atom}entry')
            try:
                url = root[104].get('href')
                flag = True
            except:
                print("No more members in knesset:", self.knesset_number)

            for ind, entry in enumerate(entries):
                idx += 1
                # Get the ID and position of the knesset member
                person_id = entry[10][0][1].text
                position_id = entry[10][0][2].text
                print("person id:", person_id, "position id:", position_id)

                # Expand details about the current knesset member
                url_person = 'https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Person()?$filter=PersonID%20eq%20' + str(
                    person_id)
                with urllib.request.urlopen(url_person) as response:
                    xml_data = response.read()
                root = ET.fromstring(xml_data)
                properties = \
                    root.find('{http://www.w3.org/2005/Atom}entry').find('{http://www.w3.org/2005/Atom}content')[0]
                first_name = properties[2].text
                last_name = properties[1].text
                gender = properties[4].text
                print("first name:", first_name, "last name:", last_name)

                # Expand position about the current knesset member
                url_position = 'https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Position()?$filter=PositionID%20eq%20' + str(
                    position_id)
                with urllib.request.urlopen(url_position) as response:
                    xml_data = response.read()
                root = ET.fromstring(xml_data)
                properties = \
                    root.find('{http://www.w3.org/2005/Atom}entry').find('{http://www.w3.org/2005/Atom}content')[0]
                position_desc = properties[1].text
                print("position description:", position_desc)

                # Create knesset member
                person = self.KnessetMember(person_id, first_name, last_name, gender, position_id, position_desc)
                person.party_name = ''
                print("Knesset Number:", self.knesset_number)

                # Add the knesset member to the corresponding party
                party_id = entry[10][0][9].text

                print("party id:", party_id)
                if party_id is not None:
                    for ind, par in enumerate(self.parties):
                        if par.party_id == party_id:
                            person.party_name = par.party_name
                            self.parties[ind].party_members.append(person)

                members_df.loc[idx] = [self.knesset_number, person_id, first_name, last_name, gender, party_id,
                                       person.party_name, position_id, position_desc]
                members_df.to_csv(self.save_path + '/Members_Knesset_' + str(self.knesset_number) + '.csv',
                                  encoding='utf-8-sig', index=False)
                print("Finished proccessing person number:", str(idx + 1))
        return members_df

    def populate_knesset_from_file(self, save_path, parties, members):
        # Populate committees and their protocol files
        for ind, com in enumerate(os.listdir(self.save_path)):
            if '.csv' not in com:
                committee = self.Committee(com, [])
                com_path = f'{save_path}/{str(com)}'
                convert_word_doc_to_docx(com_path)
                for doc in os.listdir(com_path):
                    committee.committee_protocols.append(f'{com_path}/{str(doc)}')
                self.committees.append(committee)

        # Populate parties
        parties = parties[parties['Knesset_num'] == self.knesset_number]
        for p in range(len(parties)):
            party_cur = parties.iloc[p, :]
            party = self.Party(party_cur['Party_ID'], party_cur['Party_name'], party_cur['Start_date'],
                               party_cur['Finish_date'])
            self.parties.append(party)

        # Populate knesset members
        members = members[members['Knesset Number'] == self.knesset_number]
        for m in range(len(members)):
            member_cur = members.iloc[m, :]
            member = self.KnessetMember(member_cur['Member ID'], member_cur['First Name'], member_cur['Last Name'],
                                        member_cur['Gender'], member_cur['Role ID'], member_cur['Role Desc'])
            if str(member_cur['Role ID']) == '54':
                self.knesset_members.append(member)
            party_id = member_cur['Party ID']
            if str(party_id) != 'nan':
                for ind, par in enumerate(self.parties):
                    if int(party_id) == par.party_id:
                        self.parties[ind].party_members.append(member)

    # Analysis functions
    def summarize_committees_length_and_amount(self):
        for ind, com in enumerate(self.committees):
            avg_len = 0
            meetings_counter = 0
            for meeting in self.committees[ind].committee_meetings:
                if meeting.meeting_length != 0:
                    avg_len += meeting.meeting_length
                    meetings_counter += 1
            if meetings_counter > 0:
                avg_len = avg_len / meetings_counter
                self.committees[ind].committee_avg_meeting_length = avg_len
                self.committees_summary = pd.concat([self.committees_summary, pd.DataFrame(
                    np.array([com.committee_name, com.num_of_committee_meetings, avg_len]).reshape(1, -1),
                    columns=self.committees_summary.columns)])
        print(f"Committees of Knesset {self.knesset_number} Summary: ")
        print(self.committees_summary)

    def get_committees_structure_by_parties(self):
        # Loop through all committees of the knesset, for each committee loop through all its meetings
        # and add committee members to their party list if they don't already appear there
        for committee in self.committees:
            for meeting in committee.committee_meetings:
                for member, party in meeting.participants_parties.items():
                    # Add a party that wasn't seen yet
                    if party not in committee.committee_members_by_parties.keys():
                        committee.committee_members_by_parties[party] = []
                    # Add a member to its party if not already there
                    if member not in committee.committee_members_by_parties[party]:
                        committee.committee_members_by_parties[party].append(member)

            # Count the number of members in each party in the committee
            for party, member in committee.committee_members_by_parties.items():
                committee.num_of_members_per_party[party] = len(committee.committee_members_by_parties[party])


if __name__ == "__main__":
    path_knesset = r'D:\yotam\knesset'
    url_knesset = 'http://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Committee()?$filter=KnessetNum%20eq%20'
    committees_url = 'https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Faction()?$filter=KnessetNum%20eq%20'
    members_url = 'https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_PersonToPosition()?$filter=KnessetNum%20eq%20'
    create_folders_flag = False

    if create_folders_flag:
        create_folders_knessets_and_committees(path_knesset, url_knesset)
    knesset_list = populate_all_knessets_from_ready_files(path_knesset, committees_url, members_url, save_flag=False)
    knesset_list = process_all_protocols(path_knesset, knesset_list[-5:], error_save_flag=False)
    knesset_list = aggregate_sentiments(knesset_list)
    sentiment_df = create_sentiment_df(knesset_list)
    sentiment_df.to_csv(f'{path_knesset}/Sentiment_Analysis_df.csv', index=False, encoding='utf-8-sig')
    # Translate all text to english
    # translate_all(knesset_list)

    # Search and plot for statement frequency by date and by knessets num and committees
    search_saying = 'למה'
    get_statement_frequency_by_time(knesset_list[-5:], search_saying)
    # Plot a specific committee parties representation
    knesset_list[4].committees[9].plot_parties_representation_in_committee()
    # Plot a specific committee speaking frequency of participants
    knesset_list[4].committees[9].plot_speaking_frequency_in_committee(participants=True, percentage=True)
    # Plot a specific committee speaking frequency of parties
    knesset_list[4].committees[9].plot_speaking_frequency_in_committee(participants=False, percentage=False)
    # Print sentiment analysis of a specific committee meeting by each participant
    print(knesset_list[4].committees[9].committee_meetings[3].participants_sentiments)



