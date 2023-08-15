# -*- coding: utf-8 -*-
"""
Created on Tue Mar 23 16:26:51 2021

@author: Armando Anzellini

Looks for citations in PDF file and extracts text. Can select to create a word
cloud from multiple PDF files or extract paragraph and sentence in which citation
is found.

"""
import re
import math
import base64
import traceback
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from copy import deepcopy
from wordcloud import WordCloud, STOPWORDS
import PyPDF2
import pytesseract
from pdf2image import convert_from_bytes, convert_from_path
from io import BytesIO

st.title('PDF Citation Scraper')

# Get authors and years to look for
refs  = st.text_input('Last names (optional initials) and years separated by semicolons with a pipe character (|) denoting a new reference (e.g., Walker, P; 2005| Saini; Srivastava; Rai; Shamal; Singh; and Tripathi; 2012): ')
keywords = st.text_input('Keywords separated by a comma: ')
simult   = st.checkbox('Check box if keywords and authors should be searched in the same sentence.')

# Ask user to upload a file
uploaded_files = st.file_uploader("Upload single or multiple PDFs...", type="pdf", accept_multiple_files=True)

pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

# direct = 'C:\\Users\\arman\\OneDrive\\Documents\\AuthorPapers (in progress)\\Forensic Assumptions\\Calibration-PDFs\\'

# file = open(direct + 'Sawchuck-et-al_2019.pdf', 'rb')

# refs     = 'Trotter and Gleser;1952'

# keywords = ''

# take references as input and parse
refs = refs.replace(' and ', '; ') # remove 'and's at the beginning to make parsing easier
refs = refs.replace(';;', ';') # remove double commas coming from above

# Make refs into a list
initial_reflist = refs.split('|')
initial_reflist = [i.split(';') for i in initial_reflist]
 
# separate and remove initials from this list
auth_list = []
for item in initial_reflist:
    auth_list += [[i.split(',') for i in item]]
     
# select only the last names to create the reflist
reflist = []
for i in range(len(auth_list)):
    temp = []
    for j in auth_list[i]:
        temp += [j[0].title().strip()] # remove extra spaces and ensure title case
    reflist += [temp]

ref = reflist[0]       

# Define the class and associated functions
class pdf_scraper():
    def __init__(self, file, ref, keywords, together):
        self.file     = file
        self.ref      = ref
        self.together = together
        
        # check if value has been given before turning into list
        if not refs:
            self.empty_ref = True # give a value to be checked later if empty
        else:
            self.empty_ref = False
            
        # check if keyword values have been given
        if not keywords:
            self.empty_kw = True # give a value to be checked later if empty
        else:
            self.empty_kw = False 

        #split the keywords and clean up for searching
        keywords = keywords.split(',')
        keywords = [k.strip() for k in keywords]

        self.keywords = keywords

    def text_extract(self):
        
        file = self.file.read()
        
        lines=[]
        #with open(file.read(), 'rb') as pdf:
        with BytesIO(file) as pdf:
            pdf_reader = PyPDF2.PdfFileReader(pdf)
            num_pages = pdf_reader.numPages
    
            # Iterate through each page of the PDF
            for page_num in range(num_pages):
                # Convert the page to an image
                images = convert_from_bytes(file, dpi=300, first_page=page_num+1, last_page=page_num+1)
    
                # Perform OCR on each image
                ocr_text = pytesseract.image_to_string(images[0])
            
                # Process the OCR tex t
                ocr_lines = re.split(r'\.([A-Z].*?\.)', ocr_text)
        
                # Filter out lines that represent tables or graphs
                filtered_lines = [line for line in ocr_lines if not all(char.isnumeric() for char in line)]
            
                # Add the filtered lines to the main lines list
                lines += filtered_lines
                
        seen = set()
        lines = [line for line in lines if not (line in seen or seen.add(line))]
        lines = [re.sub(r'-\n', '', line) for line in lines]
        lines = [re.sub(r'\n', ' ', line) for line in lines]
        lines = [line.strip() for line in lines]
        
        txt = []
        current_sentence = ""
        
        for line in lines:
            line = line.strip()  # Remove leading/trailing whitespace
        
            if not line.endswith('.'):
                current_sentence +=  line
            else:
                current_sentence +=  line
                txt.append(current_sentence)
                current_sentence = ""
                
        st.write(lines)
    
        # find references section and separate from text
        ref_lim = -1
        for i in range(len(txt)):
            if txt[i]['text'].casefold() == 'references':
                ref_lim = i
            elif txt[i]['text'].casefold() == 'literature cited':
                ref_lim = i
            elif txt[i]['text'].casefold() == 'literature c1 ted':
                ref_lim = i
            elif txt[i]['text'].casefold() == 'acknowledgment':
                ref_lim = i
            elif txt[i]['text'].casefold() == 'acknowledgments':  
                ref_lim = i
                
                
        works_cited = txt[ref_lim:]
        text        = txt[:ref_lim]
       
        # Change all emdashes into actual dashes
        for i in range(len(works_cited)-1):
            if works_cited[i]['text'] == 'e':
                add = '-' + works_cited[i+1]['text']
                works_cited[i-1]['text'] += add
                works_cited[i]['text']    = '' # remove the dash character
                works_cited[i+1]['text']  = '' # remove the number after unorphaning
            elif txt[i]['text'] == 'd':
                add = ' - ' + txt[i+1]['text']
                txt[i-1]['text'] += add
                txt[i]['text']    = '' # remove the dash character
                txt[i+1]['text']  = ''
        
        # clean all the newly empty spaces in works_cited
        works_cited = [i for i in works_cited if i['text']]
        
        # fix all references that are split mid-word
        for i in works_cited:
            i['text'] = i['text'].strip('-')
    
        # don't sort references because italics are sometimes set as different font
        # May be the same for text!!!!
        
        # select only the text for the references info
        references = ''
        
        for i in works_cited:
            references += i['text'] + '\n'
        
        brack = r'\[\d{,2}\]|'
        paren = r'\(\d{,2}\)|'
        naked = r'\d{,2}\.[ ][A-Z]'
        
        pattern = r'\n(?=' + brack + paren + naked + ')'
        
        references = re.split(pattern, references)
        
        references = references[1:] # remove the heading from the list
        
        # clean up spaces before closing parentheses, brackets, commas, and double spaces
        cites = []
        for r in references:
            c = r.replace('\n', ' ')
            c = c.replace(' )', ')')
            c = c.replace(' ]', ']')
            c = c.replace(' ,', ',')
            c = c.replace('  ', ' ')
            c = c.replace(' – ', '-')
            c = c.replace(' .', '.')
            # clean up number ranges whose dashes have been removed
            c = re.sub(r'(?<=\d)\s(?=\d)', '-', c)
            # clean up fi and ff when separated from word
            c = c.replace(' fi ', 'fi')
            c = c.replace(' ff ', 'ff')
            cites += [c]
       
        # Now clean up cites if it's separating at issue number (#)
        posslst  = ('(', '[')
        moved    = []
        i=0
        while i < len(cites)-1:
            if not cites[i][0].isdigit():
                if cites[i][0] != cites[i+1][0] and cites[i].startswith(posslst):
                    cites[i] += cites[i+1]
                    i+=1
                    moved += [i]
                else:
                    i += 1
            else:
                i += 1
       
        strts = []
        for i in cites:
            strts += i[0]
            
        count1 = strts.count('[')
        count2 = strts.count('(')
        
        check = ''
        
        if count1 > count2:
            check += '['
        elif count1 < count2:
            check += '('
        
        if check in posslst:
            indices = [index for index, element in enumerate(strts) if element == check]
        else:
            indices = [index for index, element in enumerate(strts)]
    
        cites = [cites[ix] for ix in indices]
    
        # Fixing text now
        # fix when only a 'd' appears (it's a dash) and strip dashes at midword 
        # breaks and add a space after each blcok if not splitting word
        for i in range(len(text)-1):
            if text[i]['text'] == 'e':
                add = '-' + text[i+1]['text']
                text[i-1]['text'] += add
                text[i]['text']    = '' # remove the dash character
                text[i+1]['text']  = ''
            elif text[i]['text'] == 'd':
                add = ' - ' + text[i+1]['text']
                text[i-1]['text'] += add
                text[i]['text']    = '' # remove the dash character
                text[i+1]['text']  = ''
        
       
        # clean up headings that may have been picked up as paragraph (all caps)
        txt = [i for i in text if not i['text'].isupper()]
        
        # clean up all the newly blank text spaces
        txt = [i for i in txt if i['text']]
        
        # clean up text if period at end of text is preceded by not a word
        pattern = r'\s[a-z]\.'
        for i in txt:
            i['text'] = re.sub(r'(?<=\s[a-z])(\.)', '', i['text'])
            
        # skip if any of the given words are found at end so period is not caught
        skip = ['Dr.', 'U.S.', 'pp.', 'et al.', 'e.g.']
        for i in txt:
            if i['text'].endswith(tuple(skip)):
                i['text'] += ' '
        
        # sorting even if possibly losing some italicized information. Fix later by fixing font tags           
        # instead go by sentences since sentences are most important and paragraphs can be sectioned
        txt_sort = sorted(txt, key = lambda x: x['tag'])
        
        # get dictionary of indices for each tag type in sorted text list
        keys = sorted(set([entry['tag'] for entry in txt_sort]))
        
        tagints = {key: None for key in keys} # dict of tag intervals
        
        i = 0
        while i < (len(txt_sort)-1):
            k = i
            while i <= k < (len(txt_sort)-1):
                if txt_sort[k]['tag'] != txt_sort[k+1]['tag']:
                    tagints[txt_sort[k]['tag']] = [i, k+1]
                    k += 1
                    break
                else:
                    k += 1
            i = k
        
        # add the interval for the last key
        last_key = list(tagints.keys())[-1]
        last_val = tagints[list(tagints.keys())[-2]][1]
        
        tagints[last_key] = [last_val, len(txt_sort)]  
            
        # clean tagints if some intervals are None
        # This happens from changing e and d to dashes
        ints = {k: v for k, v in tagints.items() if v is not None}
        
        # Find the interval for each paragraph by index and whithin tag intervals
        idx   = {key: None for key in sorted(ints.keys())}
        
        paras = []
        
        for key in ints:
            i = ints[key][0]
            while i < ints[key][1]:
                # if not complete sentence, find next block ending in a period
                add = [txt_sort[i]['page']]
                par = ''
                k = i
                while i <= k < ints[key][1]:
                    if txt_sort[k]['text'].endswith('.'):
                        par   += txt_sort[k]['text']
                        add   += [par]
                        paras += [add]
                        break
                    elif txt_sort[k]['text'].endswith('(') or txt_sort[k]['text'].endswith('['): # don't add space after parenthesis
                        par += txt_sort[k]['text']
                        k += 1
                    elif txt_sort[k]['text'].endswith('-'):
                        par += txt_sort[k]['text'].rstrip('-')
                        k += 1
                    else:
                        par += txt_sort[k]['text'] + ' '
                        k += 1
                i = k+1   
        
        # clean up spaces before closing parentheses, brackets, commas, and double spaces
        for p in paras:
                p[1] = p[1].replace(' )', ')')
                p[1] = p[1].replace(' ]', ']')
                p[1] = p[1].replace(' ,', ',')
                p[1] = p[1].replace('  ', ' ')
                p[1] = p[1].replace('–', '-')
                p[1] = p[1].replace('- ', '-')
                p[1] = p[1].replace(' -', '-')
                p[1] = p[1].replace(' – ', '-')
                # clean up number ranges whose dashes have been removed
                p[1] = re.sub(r'(?<=\d)\s(?=\d)', '-', p[1])
                # clean up fi and ff when separated from word
                p[1] = p[1].replace(' fi ', 'fi')
                p[1] = p[1].replace(' ff ', 'ff')
        
        return paras, cites

    def find_citations(self, paras, cites):
        ref = self.ref
        
        # separate authors and years
        auth = ref[:-1]
        year = ref[-1:][0]
        
        # Count how many authors and create patterns for citations as expected
        if len(auth) == 1:
            authpat  = f'{auth[0]}'
        elif len(auth) == 2:
            authpat  = [f'{auth[0]} and {auth[1]}']
            authpat += [f'{auth[0]} & {auth[1]}']
        elif len(auth) > 2:
            authpat  = [f'{auth[0]} et al.']
            if len(auth) <= 5:
                authpat += [', '.join(auth[:-1]) + f' and {auth[-1]}']
                authpat += [', '.join(auth[:-1]) + f', and {auth[-1]}']
                authpat += [', '.join(auth[:-1]) + f' & {auth[-1]}']
           
        # Find paragraphs that have the authors cited (not years yet)
        cite = []
        for pat in authpat:
            cite += [p for p in paras if pat in p[1]]
        
        # now check if the correct year is cited in those paragraphs
        yrpat = [year, f"'{year[-2:]}", f"’{year[-2:]}"]
        
        match = []
        for yr in yrpat:
            match += [c for c in cite if yr in c[1]]
        
        # do again per sentence in each paragraph to extract sentence
        skip = ['Dr.', 'U.S.', 'pp.', 'et al.']
        
        sentences = []
        for m in match:
            regexskip = [rf"(?<!\b{s.strip('.')}\b)" for s in skip]
            pattern  = ''.join(regexskip) + '(?<!\s\w)\.'
            parag    = re.split(pattern, m[1])
            authsent = []
            yrsent   = []
            for pat in authpat:
                authsent += [s for s in parag if pat in s]
            for yr in yrpat:
                yrsent   += [snt for snt in authsent if yr in snt]
            sentences += yrsent
            
        sentences = [snt.strip() for snt in sentences]
        
        # find out if pdf has numbered citations
        # function that finds location of reference authors and year and gets ref number
        def ref_num(paragraph, auth, year):
            foo = r''    # start regex expression for ref number
            for i in auth:
                foo += '(?:%s)\D+' % i # add all authors to regex exp 
            foo += '.*' + f'(?:{year}).+[^\[\d]'     # add year at the end of the regex expression
            found = re.search(foo, paragraph, re.IGNORECASE)    # find starting location
            if found:
                loc     = found.span()
                cite    = paragraph[0:loc[1]]
                r_num   = re.match(r'\W*(\d{1,2})[\.|\]]', cite) # extract reference number
                ref_num = re.findall(r'\d{1,2}', r_num.group())[0]
            else:
                ref_num = ''
            return ref_num, ', '.join(auth) + f', {year}'
            
        # use func to find the ref_num if numbered references present
        if cites:
            for c in deepcopy(cites):
                cite_num, cite = ref_num(c, auth, year)
                if cite_num:
                    num_ref  = [cite_num, cite]
                    break
                else:
                    cite_num = ''
                    num_ref  = []
        elif not cites:
            cite_num = ''
            num_ref  = []
        
        # use regex to find where number ranges between brackets may include cite num
        range_cite = []
        try:
            for paragraph in paras:
                pattern    = r'[\[|\(|,|\w|\s](\d{,2}[-|–]\s*\d{,2})[\]|\)|,)]' # either long or short dash
                posranges  = re.findall(pattern, paragraph[1])
                for dash in posranges:
                    rango     = re.split(r'-|–', dash)
                    if int(rango[0]) <= int(cite_num) <= int(rango[1]):
                        range_cite += [f'{dash}']
        except ValueError:
            range_cite = []
        
        # defining regex function to find sentences with numbered citations
        def num_match(paragraph, refnum):
            pattern = r'[\[|\(|,|\s]' + refnum + '[\]|\)|,)](?!\d{3})'
            sentences = []
            temp_i = re.split(r'\.\s(?=[A-Z])', paragraph[1])
            for s in temp_i:
                if re.search(pattern, s):
                    sentences += [s]
            return sentences
        
        # defining function that finds sentences with the ref intervals
        def range_match(paragraph, ref_interval):
            pattern = rf'[\[|\(|,]({ref_interval})[\]|\)|,]'
            sentences = []
            temp_i = re.split(r'\.\s(?=[A-Z])', paragraph[1])
            for s in temp_i:
                if re.search(pattern, s):
                    sentences += [s]
            return sentences    
        
        # Get sentences if citations are numbered or have a range
        if cite_num:
            for paragraph in paras:
                sentences += num_match(paragraph, cite_num)
                    
        if range_cite:
            for r in range_cite:
                for paragraph in paras:
                    sentences += range_match(paragraph, r)
        
        # remove any duplication of sentences
        ref_sentences = list(set(sentences))
        
        return ref_sentences, num_ref
    
    def find_keywords(self, paras):
        
        def keyword_match(paragraph, word):
            sentences = []
            temp_i    = re.split(r'\.\s(?=[A-Z])', paragraph[1])
            pattern   = rf'{word}[\s|\W]'
            for s in temp_i:
                if re.search(pattern, s, re.IGNORECASE):
                    sentences += [s]
            return sentences
        
        # Get sentences in which the match occurred for keywords
        # Get sentences related to all keywords     
        sentences = []
        for word in self.keywords:
            for paragraph in paras:
                sentences += keyword_match(paragraph, word)
        
        # remove any duplication of sentences
        kw_sentences = list(set(sentences))
        
        return kw_sentences

    def find_match(self):
        together        = self.together
        paras, cites    = self.text_extract()
        
        if paras == 'Image':
            return 'Image', 'Image', 'Image'
        
        # check if either refs or keywords are empty
        if not self.empty_ref:
            ref_sentences, num_ref = self.find_citations(paras, cites)
        else:
            ref_sentences = []

        if not self.empty_kw:
            kw_sentences = self.find_keywords(paras)
        else:
            kw_sentences = []
        
        sentences = []
        if together == True:
            sentences = list(set(kw_sentences) & set(ref_sentences))
        elif together == False:
            sentences = list(set(kw_sentences + ref_sentences))
            
        # Get matching paragraphs that include at least one of the sentences
        match = []
        for paragraph in paras:
            if any(sentence in paragraph[1] for sentence in sentences):
                match += [[paragraph[0], paragraph[1]]]
                
        # Sort matches by page number
        match = sorted(match, key=lambda x: x[0])
        
        return match, sentences, num_ref
    
    def return_match(self):
        ref = self.ref
        
        st.title(self.file.name.strip('.pdf'))
        st.markdown('*Finding: *' + ', '.join(ref))
        
        # catch if reading errors cause breakdown so whole app doesn't break
        try:
            match, sentences, num_ref = self.find_match()
        except Exception:
            st.markdown('_PDF text could not be read_')
            print(traceback.format_exc())
            return
        
        # show text if the sentences are returned empty
        if not sentences:
            st.markdown('_PDF text could not be read_')
            print(traceback.format_exc())
            return
        
        # this will happen if the text was loaded as an image not OCR'd
        if match == 'Image':
            st.markdown('_PDF was loaded as an image without character recognition_')
            return
               
        # Add note for numbered references
        if num_ref:
            st.markdown('**References numbered in this text as:**')
            st.markdown(f'**_{num_ref[0]} -> {num_ref[1]}_**')
        
        '''
        # Separating by sentence in paragraphs to rejoin as output
        for i in match:
            output = []
            st.markdown('**Page %s**' % i[0])
            temp_i    = re.split(r'\.\s(?=[A-Z])', i[1])
            for s in temp_i:
                if any(sentence in s for sentence in sentences):
                    highlight = '**' + s.strip() + '.**' #add markdown bold
                    output   += [highlight]
                else:
                    output   += [s +'.']
            st.markdown(' '.join(output).replace('..', '.')) # Flatten ouput list and output
        '''
        # only print sentences and forget about whole paragraph for now, can be fixed later
        for s in sentences:
            st.markdown(f'**{s}.**')

#-----------------------------------------------------------------------------      
class word_cloud():
    def __init__(self, files, ref, keywords, together):
        self.files = files
        self.ref   = ref
        self.keywords = keywords
        self.together = together
        
        ignore = ['et', 'al']
        
        # separate authors and years
        auths = ref[:-1]
        
        keywds = keywords.split(',')
        keywds = [k.strip() for k in keywds]
        
        self.stpwds = auths + keywds + ignore
                
    def run(self):
        files    = self.files
        ref      = self.ref
        keywords = self.keywords
        together = self.together
        
        stopwords = set(STOPWORDS)
        stopwords.update(self.stpwds)
        
        words  = []
        fnames = []
        errors = []
        
        for file in files:
            try:
                match, sentences, num_refs = pdf_scraper(file,
                                                         ref,
                                                         keywords,
                                                         together=together).find_match()
            
                fnames += [[sentences, file.name]]
            
                words += sentences
            
            except Exception:
                print(traceback.format_exc())
                errors += [file.name]
        
        st.markdown(words)
        
        # check to make sure you have at least one sentence to be wordclouded
        if not words:
            st.markdown('**All files encountered errors in text extraction and/or citation matching**')
            print(traceback.format_exc())
            return '', ''
        
        # Compile the words into a single paragraph to word cloud
        text = ' '.join(words)
        
        # Set traits for word cloud
        wc = WordCloud(background_color="white",
                       colormap="viridis", 
                       stopwords=stopwords).generate(text)
        
        # Create word counts to export and download (for batch of files)
        counts = WordCloud(stopwords=stopwords).process_text(text)
        
        count_df = pd.DataFrame.from_dict(counts, orient='index', 
                                                  columns = ['Count'])
        
        count_df.index.name='Words' # add title to index
        
        count_df.sort_values(by=['Count'], ascending = False, 
                                           inplace   = True) # sort values descending
        
        # create csv of sentences and PDF names
        sent_df = pd.DataFrame(fnames, columns=['Sentences', 'PDFs'])
        
        # show the Word Cloud figure
        fig, ax = plt.subplots()
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        st.pyplot(fig)
        
        # Print a list of the files that had issues in the word cloud generator
        st.title('Files that could not be read by Word Cloud generator')
        for f in errors:
            st.markdown(f)
        
        return count_df, sent_df
            
#-----------------------------------------------------------------------------
def download_csv(dataframe, filename, display_text, index=True):
    '''
    
    Parameters
    ----------
    dataframe : TYPE
        DESCRIPTION.
    filename  : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    '''
    csv = dataframe.to_csv(index=index)
    b64 = base64.b64encode(csv.encode()).decode()  # some strings
    linko= f'<a href="data:file/csv;base64,{b64}" download="{filename}.csv">{display_text}</a>'
    st.markdown(linko, unsafe_allow_html=True)

#-----------------------------------------------------------------------------
hover_text   = 'Click Run to start the scraping'
report_hover = 'Click to export PDF report'
count_hover  = 'Click to create link and download counts table'

# Run the program if all criteria are met
if refs or keywords and uploaded_files:
    run    = st.button('Run', help=hover_text)
    wc     = st.button('WordCloud')
    # report = st.button('Export Report', help=report_hover)
    if run:
        for uploaded_file in uploaded_files:
            for ref in reflist:
                pdf_scraper(uploaded_file, ref, keywords, together=simult).return_match()
    if wc:
        counts, sent = word_cloud(uploaded_files, ref, keywords, together=simult).run()
        fname = refs.replace(' ', '').replace(';', '').replace('|', '')
        if not counts.empty:
            st.title('Download CSV output files')
            download_csv(counts, fname +'_Counts', 
                             'Download CSV of Counts')
        if not sent.empty:
            download_csv(sent, fname + '_Sentences', 
                             'Download CSV of Sentences', 
                                 index=False)



