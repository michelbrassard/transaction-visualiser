import pdfplumber as pdf
import pandas as pd

def extractLines(semicleanData_list, croppedPage):
    for row in croppedPage.extract_text_lines(x_tolerance = 1):
        text = row['text']
        if text.startswith('MO I PNB:') or len(text) <= 32: #x_tolerance helps with adding the space between the date and the reference number
            continue
        semicleanData_list.append(text)


#IF THE MONTH IS 1 SET YEAR TO THE PREVIOUS ONE BECAUSE ON JAN YOU GET FOR DECEMBER
def findYear(documentPath):
    issuedDate = documentPath.split("_")[1]
    
    year = issuedDate[:4]
    month = issuedDate[4:6]
    
    if month == '01':
        number_year = int(year)
        number_year = number_year - 1
        year = str(number_year)
    
    return year
        
def clean(semicleanData_list, year):
    transactions = {
        'date':[],
        'location': [],
        'amount': []
    }
    
    for line in semicleanData_list:
        if line.startswith("STANJE PRETHODNOG IZVJEŠĆA"):
            continue
        lineData = line.split(" ")
        lineData.pop(1)
        
        #extract the amount on money
        try:
            amount = float(lineData.pop(-1).replace(".", "").replace(",", "."))
        except ValueError:
            continue
        if amount > 0:
            try:
                checkAmount = float(lineData.pop(-1).replace(".", "").replace(",", "."))
                amount = checkAmount
            except ValueError:
                print("Exception with parsing on line: " + line)
                
        #extract the date
        dayMonthValues = lineData.pop(0).split(".")
        day = dayMonthValues[0]
        month = dayMonthValues[1]
        year = year.replace(".", "")
        
        date = "{}-{}-{}".format(year, month, day)
        
        #extract where/why money was spent      
        location = ' '.join(lineData)
        transactions['date'].append(date)
        transactions['location'].append(location)
        transactions['amount'].append(amount)
    
    return transactions

# use this 
def parseDocument(documentPath, fileName):
    semicleanData = []
    
    with pdf.open(documentPath) as document:
        first_page = document.pages.pop(0) 
        cropped = first_page.within_bbox((0, 350, first_page.width, 600))
        year = findYear(documentPath=fileName)
        extractLines(semicleanData_list = semicleanData, croppedPage = cropped)
        
        #extract other pages
        for page in document.pages:
            cropped = page.within_bbox((0, 100, page.width, 800))
            extractLines(semicleanData_list = semicleanData, croppedPage = cropped)
        
        dict_transactions = clean(semicleanData_list = semicleanData, year = year)
        
        df_transactions = pd.DataFrame.from_dict(dict_transactions)
        df_spending_data = df_transactions[df_transactions['amount'] < 0]
        
        # this generates an error
        # SettingWithCopyWarning:
        # A value is trying to be set on a copy of a slice from a DataFrame.
        # Try using .loc[row_indexer,col_indexer] = value instead
        df_spending_data.loc[:, "amount"] *= -1
        
        print("parsing finished")
        
        return pd.DataFrame.from_dict(df_spending_data)