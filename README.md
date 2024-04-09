# WebScarping_NLP-Israeli_Knesset

The project focuses on the Israeli parlament the "Knesset".
The Knesset is composed of 120 knesset members each belonging to a certain party,
a combination of parties that have at least 61 members - can agree to form a calition and the Israeli government.
After forming the coalition, the Knesset members are divided into committees managing the countrie's matters.
The committees' protocols are open to the public: https://main.knesset.gov.il/Activity/committees/Pages/AllCommitteeProtocols.aspx

The purpose of the project was to analyze the statements of the Israeli Knesset members - 
positive, negative and neutral scores and aggregate the results by different sections:
personal, party, committee and knesset sitting.

The project combines webscraping and sentiment analysis.
The first part focused on downloading all committees' protocols from the web and arranging them in a logical manner
that will allow analysis of the data efficiently.
The second part, went through all protocols and knesset members' statements, associated each statement to a member,
translated statements from Hebrew to English and ran a sentiment analysis algorithm - aggregating results by member,
party and committee. The user can query and get visual analysis of the results by the wanted section.
In addition, I anaylyzed the "involvement" of each member/party in the committees - 
analyzing the frequency of statements in the committees.

The "Sentiment_Analysis_df" csv file includes the sentiment analysis and frequency analysis by each knesset member.

