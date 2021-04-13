# -*- coding: utf-8 -*-
"""
Created on Tue Mar 23 16:26:51 2021

@author: Armando Anzellini

Notes from Mark and Colleen Meeting:
Find paper on logistic regression over discriminant function for sex estimation

Stats may be problematic, how stats are used, who did it first?
How stats are interpreted

Use keywords as well from API search

We'll have search terms as well to search and how they change over time to be
able to really follow it back

"""
import fitz
import streamlit as st


st.title('PDF Citation Scraper')
# Get authors and years to look for
authors = st.text_input('Last names as shown in citation (e.g., Walker and Bass *or* Sieni et al.): ')
year = st.number_input('Year of citation: ', value = 1950, step = 1)

# Ask user to upload a file
uploaded_file = st.file_uploader("Choose a PDF...", type="pdf")

# Define the class and associated functions
class pdf_scraper(object):
    def __init__(self, file, authors, year):
        self.file    = file
        self.citations = (authors + ', ' + str(year), authors + ' (%s)' % str(year))
        
    def find_match(self):
        
        citations = self.citations # redefine for ease of function
        
        # Open the pdf as text per page and per paragraph (return [page, paragraph])
        with fitz.open(stream=self.file.read(), filetype = "pdf") as doc: # opening BytesIO stream
            text = []
            for page in doc:
                text += [[page.number + 1, page.get_text("blocks")]]
            doc.close()
                
        # Remove unneccessary tuple values from paragraph and clean up for readability
        paras = []
        for i in text:
            for j in i[1]:
                paras += [[i[0],j[4].replace('\n', ' ').replace('- ', '')]]
                
        # Remove any paragraphs that are smaller than 50 characters
        # This prevents titles of journals and headers from being included
        paras = [i for i in paras if len(i[1]) > 61]
        
        # Remove any paragraph beginning with Fig and image
        paras = [i for i in paras if not i[1].startswith('Fig')]
        paras = [i for i in paras if not i[1].startswith('<image')]
        
        # Remove any paragraph that is just affiliation or information
        paras = [i for i in paras if not i[1].startswith('Grant sponsor:')]
        paras = [i for i in paras if not i[1].startswith('*Correspondence')]
        paras = [i for i in paras if not i[1].startswith('Received')]
        paras = [i for i in paras if not i[1].startswith('DOI:')]
        paras = [i for i in paras if not i[1].startswith('TABLE')]
        
        # Remove paragraphs that are mostly digits since they represent a table
        for i in paras:
            numcount = sum(c.isdigit() for c in i[1])
            letcount = sum(c.isalpha() for c in i[1])
            if numcount > letcount:
                paras.remove(i)
        
        # Find all paragraphs where citation is found and return paragraph and page in list
        match  = [s for s in paras if citations[0] in s[1]]
        match += [s for s in paras if citations[1] in s[1]]
        
        # Make sure paragraphs are not orphaned by finding the continuation on next pg
        for i in match:
            if i[1][-2] != '.':
                ix = paras.index(i)
                i[1] += paras[ix + 1][1]  # only returns start page of paragraph
        
        # Make sure paragrpahs start correctly not in the middle of a sentence
        for i in match:
            if not i[1][0].isupper():
                ix = paras.index(i)
                i[1] = paras[ix - 1][1] + i[1]
                
        # Sort matches by page number prior to finding sentences
        match = sorted(match, key=lambda x: x[0])
            
        # Get sentences in which the match occurred for citations
        # Create function to simplify implementation of this finding
        def find_sentence(string, sub):
            sub_start = string.find(sub)
            start = 0
            end   = 0
            for i in range(sub_start, len(string)):
                if string[i:i + 2] == '. ':
                    end = i + 1
                    break
            for i in range(sub_start, 0, -1):
                if string[i:i + 2] == '. ':
                    start = i + 2
                    break
            return start, end
        
        # implement function to find the sentences related to citation[0]
        sentences = []
        for i in match:
            sent_loc = find_sentence(i[1], citations[0])
            sent = i[1][sent_loc[0]:sent_loc[1]]
            sentences += [sent]
            
        # do the same as above implementing function to find citation[1]
        for i in match:
            sent_loc = find_sentence(i[1], citations[1])
            sent = i[1][sent_loc[0]:sent_loc[1]]
            sentences += [sent]
        
        # define function that finds the index of a duplicated value in a list
        def duplicates(lst, item):
            return [i for i, x in enumerate(lst) if x == item]
        
        # split match list into pages and txt to find duplicated texts
        pgs = []
        txt = []        
        for i in match:
            pgs += [i[0]]
            txt += [i[1]]
            
        # go through txt to find duplicated values and drop from pgs and txt
        dup_ix = []
        for j in range(len(txt)):
            x = duplicates(txt, txt[j]) # use function above to get ix of dups
            dup_ix  += [[y for y in x if len(x) >=2]] #only collect dupd ixs
            
        dup_ix  = list(filter(None, dup_ix)) # remove all empty items
        dup_ix  = set([item[1] for item in dup_ix]) # remove duplicate ixs keep last
            
        # Now use collected indices to remove the duplicated values from match
        for i in sorted(list(dup_ix), reverse=True):    # reversed to avoid changing indices
            match.pop(i)
            
        sentences = list(set(sentences))
        
        return match, sentences

    def return_match(self):
        # Return in word document? html? streamlit print? with sentence bolded within
        # the given paragraph and report the page number
        
        match, sentences = self.find_match()
        
        st.title(self.file.name + ' Finding: ' + str(self.citations))
        # Loop over all matches and return the formatted paragraphs
        for i in match:
            output = []
            sent_ixs = []
            for j in sentences:
                strt = i[1].find(j)
                if strt != -1:
                    end  = strt + len(j)
                    sent_ixs += [strt, end]
            sent_ixs.sort()
            st.markdown('**Page %s**' % i[0])
            if sent_ixs[0] != 0:
                output += [i[1][:sent_ixs[0]]] #add beginning of string to output
            for k, l in enumerate(sent_ixs[:-1]):
                #enumerate to subsequently add the sentences and between sentences to output
                output += [i[1][l:sent_ixs[k+1]]]
            if sent_ixs[-1] != 0:
                output += [i[1][sent_ixs[-1]:]] # add end of string to output
            if sent_ixs[0] == 0: # if match sentences start @ beginning of paragraph
                for x in range(len(output)): 
                    if x % 2 == 0:  # if the index of output is even
                        output[x] = '**' + output[x] + '**' # add markdown bold
            elif sent_ixs[0] != 0: # if match sentences start @ beginning of paragraph
                for x in range(len(output)): 
                    if x % 2 != 0:  # if the index of output is odd
                        output[x] = '**' + output[x] + '**' # add markdown bold
            # Flatten ouput list into a single string for output and write to st
            st.markdown(''.join(output))
                         
#------------------------------------------------------------------------------

hover_text = 'Click Run to start the scraping'

# Run the program if all criteria are met
if None not in {uploaded_file, authors, year} and st.button('Run', help=hover_text):  
    pdf_scraper(uploaded_file, authors, year).return_match()
    
