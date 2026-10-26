"""Rebuild the verified question bank from the supplied course files.
Development only: pip install openpyxl numpy scipy.
"""
from pathlib import Path
import json, sqlite3, collections
import openpyxl
import numpy as np
from scipy import stats
D=Path(__file__).parent/'data'
Q=[]
def add(topic,case,title,prompt,answer,method,rule,files,code='',numeric=None):
 q=dict(id=f'Q{len(Q)+1:03}',topic=topic,case=case,title=title,prompt=prompt,answer=answer,method=method,rule=rule,files=files,code=code,minutes=3)
 if numeric is not None:q['numeric']=numeric
 Q.append(q)
ny='NYC_Film_Permits.xlsx'
w=openpyxl.load_workbook(D/ny,read_only=True,data_only=True)
rows=list(w.active.values);header=rows.pop(0); rows=[dict(zip(header,r)) for r in rows if r[0] is not None]
n=len(rows);shoot=[r for r in rows if r['EventType']=='Shooting Permit']
def excel(title,prompt,value,formula,rule):
 add('Excel','NYC permits',title,prompt,str(value),'Use the original NYC_Film_Permits sheet. '+rule,rule,[ny],formula,value if isinstance(value,(float,int)) else None)
excel('Count the records','How many data records are in the NYC permits sheet? Exclude the header.',n,'=COUNTA(A2:A33503)','Count the identifier column and exclude the header.')
excel('Missing ZIP codes','How many records have an empty ZipCode cell?',sum(r['ZipCode'] in (None,'') for r in rows),'=COUNTBLANK(N2:N33503)','A missing ZIP code is different from an invalid or multiple ZIP code.')
types=collections.Counter(r['EventType'] for r in rows)
excel('Most common event','Which EventType occurs most often?',types.most_common(1)[0][0],'Create a PivotTable: Rows = EventType; Values = Count of EventID. Sort descending.','Use counts of records, not sums of identifier values.')
excel('Two conditions','How many Shooting Permit records are in Brooklyn?',sum(r['Borough']=='Brooklyn' for r in shoot),'=COUNTIFS(B2:B33503,"Shooting Permit",H2:H33503,"Brooklyn")','COUNTIFS applies all conditions to the same row. Counting only Brooklyn includes other event types.')
excel('Student films','How many shooting permits have Category equal to Student?',sum(r['Category']=='Student' for r in shoot),'=COUNTIFS(B2:B33503,"Shooting Permit",K2:K33503,"Student")','Inspect the actual category labels before choosing a condition.')
dur=[(r['EndDateTime']-r['StartDateTime']).total_seconds()/3600 for r in shoot]
excel('Permit duration','Find the mean shooting-permit duration in hours, rounded to the nearest half hour.',round(np.mean(dur)*2)/2,'In O2: =(D2-C2)*24\nFill down. Then: =MROUND(AVERAGEIF(B2:B33503,"Shooting Permit",O2:O33503),0.5)','Excel date differences are in days: multiply by 24 for hours.')
db='Chinook_Sqlite.sqlite'
sqls=[
('Invoice count','How many invoices are in Invoice?','SELECT COUNT(*) AS invoices FROM Invoice;','COUNT(*) counts rows including rows with NULL in other fields.'),
('Above the threshold','How many invoices have Total strictly greater than 20?','SELECT COUNT(*) AS invoices FROM Invoice WHERE Total > 20;','Use > for strictly greater than. >= includes the boundary.'),
('Between two values','How many invoices have Total > 10 and Total < 20?','SELECT COUNT(*) AS invoices FROM Invoice WHERE Total > 10 AND Total < 20;','BETWEEN includes both endpoints. Use strict inequalities when the question excludes them.'),
('Country selection','How many invoices have BillingCountry in Brazil, Argentina or Chile?','SELECT COUNT(*) AS invoices FROM Invoice WHERE BillingCountry IN (\'Brazil\',\'Argentina\',\'Chile\');','IN matches any listed value. AND cannot require one field to equal three countries.'),
('Missing company names','How many customers have a non-NULL Company?','SELECT COUNT(Company) AS customers FROM Customer;','COUNT(column) excludes NULL; COUNT(*) counts every row.'),
('Country revenue','Return the five billing countries with the highest total invoice value. Break ties alphabetically.','SELECT BillingCountry, ROUND(SUM(Total),2) AS Revenue FROM Invoice GROUP BY BillingCountry ORDER BY SUM(Total) DESC, BillingCountry LIMIT 5;','GROUP BY defines one output row per country; sum invoice totals before ranking.'),
('Downloaded albums','How many distinct albums appear in purchased invoice lines?','SELECT COUNT(DISTINCT t.AlbumId) AS albums FROM InvoiceLine AS l JOIN Track AS t ON l.TrackId=t.TrackId;','Count distinct album identifiers, not invoice lines or track identifiers.'),
('Find a silent JOIN error','A student sums Invoice.Total after joining Invoice to InvoiceLine on InvoiceId. Explain why the total is inflated and calculate the correct invoice revenue.','SELECT ROUND(SUM(Total),2) AS Revenue FROM Invoice;','Invoice.Total is at invoice level. Joining to multiple lines repeats the invoice total. SUM(DISTINCT Total) is not a safe fix: different invoices can have equal totals.')
]
for title,prompt,sql,rule in sqls:
 c=sqlite3.connect(D/db);cur=c.execute(sql);cols=[d[0] for d in cur.description];result=cur.fetchall();c.close()
 answer=str(result[0][0]) if len(result)==1 and len(cols)==1 else '\n'.join(' | '.join(map(str,r)) for r in [cols]+result)
 add('SQL','Chinook',title,prompt,answer,rule,rule,[db],sql,result[0][0] if len(result)==1 and len(cols)==1 and isinstance(result[0][0],(int,float)) else None)
for title,prompt,sql,rule in [
('Top three songs','List the names of the three longest songs, longest first. Use name as a tie-breaker.','SELECT name FROM songs ORDER BY duration_ms DESC, name LIMIT 3;','Sort before LIMIT; duration_ms measures duration, not tempo.'),
('Three simultaneous conditions','List songs with danceability, energy and valence all greater than 0.6, ordered by name.','SELECT name FROM songs WHERE danceability>0.6 AND energy>0.6 AND valence>0.6 ORDER BY name;','AND requires all three conditions; OR would include songs satisfying only one.'),
('Join without guessing IDs','List Drake songs, ordered by name, without hard-coding an artist identifier.','SELECT s.name FROM songs s JOIN artists a ON s.artist_id=a.id WHERE a.name=\'Drake\' ORDER BY s.name;','Join the foreign key to the artist key, then filter the artist name.'),
('Average tempo','Find the average tempo of all songs, to two decimals.','SELECT ROUND(AVG(tempo),2) AS tempo FROM songs;','AVG gives the arithmetic mean of non-NULL values.')
]:
 c=sqlite3.connect(D/'songs.db');result=c.execute(sql).fetchall();c.close()
 answer='\n'.join(str(r[0]) for r in result)
 add('SQL','Songs',title,prompt,answer,rule,rule,['songs.db'],sql,result[0][0] if len(result)==1 and isinstance(result[0][0],(int,float)) else None)
e2='Analytics_mindset_case_studies_ETL_Case2_Excel.xlsx';e3=e2.replace('Case2','Case3');e4=e2.replace('Case2','Case4')
etl=[
('Case 2','Location extraction','For EmployeeCode JAP1080-19M in A2, extract the location using a formula.','JAP','=LEFT(A2,3)','Case 2 uses three-letter location codes. Do not assume this is true in Case 3.',e2),
('Case 2','Employee identifier','For JAP1080-19M in A2, extract the employee ID as text.','1080','=MID(A2,4,FIND("-",A2)-4)','Extract between the three-letter location and the hyphen, rather than including the plant number.',e2),
('Case 2','Plant extraction','Extract PlantID from JAP1080-19M in A2. Keep the result as text.','19','=MID(A2,FIND("-",A2)+1,LEN(A2)-FIND("-",A2)-1)','Find the hyphen, then exclude the one-letter pay-period suffix in Case 2.',e2),
('Case 3','Repair a fixed-width rule','Why does LEFT(A2,3) fail as a general location extraction rule in Case 3? Describe a repair.','Location labels vary in length, including Canada, Japan and US. Locate the first digit and take all characters before it.','','Use character boundaries when field lengths vary. Check the resulting locations against the allowed country labels.',e3),
('Case 3','Standardise payment frequency','The Case 3 suffix can be W, We, M or Mo. How should you standardise it?','Map W and We to Weekly; M and Mo to Monthly. Extract the full trailing letter group first.','','RIGHT(A2,1) alone gives e or o for the two-letter suffixes. Validate all four variants.',e3),
('Case 4','A safe preparer lookup','Which key should connect JELineItems with PreparerInfo, and why?','Use both BusinessUnitID and PreparerID. PreparerID alone is reused between business units.','','Validate uniqueness of the combined key in PreparerInfo and preserve the journal-line count after the lookup.',e4),
('Case 4','Signed journal amounts','Credits in this case are already negative. How should Debit and Credit be combined into Amount?','Amount = Debit + Credit. Subtracting an already negative credit reverses its sign.','','Inspect the sign convention before applying an accounting formula.',e4)
]
for case,title,prompt,answer,code,rule,f in etl:add('Excel / ETL',case,title,prompt,answer,rule,rule,[f],code)
p15='Analytics_mindset_case_studies_IntegrateCo_2015payroll.csv';p16=p15.replace('2015','2016');pj='Analytics_mindset_case_studies_IntegrateCo_jobcodes.csv'
for title,prompt,ans,rule in [
('Comparable gross pay','Which 2015 fields correspond to Gross_Wages in 2016?','Reg_Pay + OT_Pay.','Match variable definitions before comparing years. Comparing only Reg_Pay with Gross_Wages omits overtime.'),
('Comparable employees','Which employee fields match between 2015 and 2016?','Emp_No in 2015 and Employee_Number in 2016. Employee_ID is a new identifier in 2016.','Names may repeat or change; use the documented common identifier.'),
('A meaningful hourly rate','How should you calculate aggregate gross pay per hour for a job code?','SUM(gross pay) / SUM(regular hours + overtime hours), for the same job code and year.','The simple mean of row-level pay rates weights small and large rows equally. Use the ratio of totals, and flag zero-hour denominators.'),
('Preserve job codes','Extract the job code from the example 14S001SG and explain its required data type.','001, stored as three-character text.','14 is the project year, S is the department, 001 is the job code and SG is the location. Preserve leading zeros.')
]:add('Excel / ETL','IntegrateCo',title,prompt,ans,rule,rule,[p15,p16,pj])
# Independent daily aggregation and OLS benchmark for the restaurant.
w=openpyxl.load_workbook(D/'data.xlsm',read_only=True,data_only=True)
def records(sheet):
 r=list(w[sheet].values);h=r.pop(0);return [dict(zip(h,x)) for x in r if x[0] is not None]
daily=collections.defaultdict(lambda:[0.,0.])
for r in records('salesData'):
 daily[r['date']][0]+=r['netTotal'];daily[r['date']][1]+=r['netTotal_364']
weather={r['date']:r['tmax'] for r in records('weatherData')}
games={r['date']:r['gameDay'] for r in records('gameData')}
dates=sorted(daily);y=np.array([daily[d][0] for d in dates])
def ols(x):
 X=np.column_stack([np.ones(len(y)),x]);beta=np.linalg.lstsq(X,y,rcond=None)[0];err=y-X@beta;df=len(y)-X.shape[1]
 se=np.sqrt(np.diag(np.linalg.inv(X.T@X))*sum(err**2)/df);p=2*stats.t.sf(np.abs(beta/se),df)
 return beta.tolist(),p.tolist(),1-sum(err**2)/sum((y-y.mean())**2)
t=ols(np.array([weather[d] for d in dates]));g=ols(np.array([games.get(d,0) for d in dates]))
method='Aggregate netTotal by date using SUM. Join weather and game data by date; code dates absent from the supplied game schedule as gameDay=0. Keep only observed sales dates (do not invent zero-sales dates). Include an intercept.'
for title,prompt,ans,rule,code,num in [
('Choose the observation','Before modelling total daily restaurant sales, what should one row represent?','One observed sales date, with netTotal summed across menu items.','An average across products measures average item sales, not total restaurant sales.','',None),
('Temperature association','Regress total daily netTotal on tmax with an intercept. Report the slope to two decimals.',f'{t[0][1]:.2f} dollars per degree Fahrenheit. n={len(y)}; p={t[1][1]:.4g}; R²={t[2]:.4f}.','This is an association in observational data; statistical significance alone does not establish causation.','Y = daily SUM(netTotal)\nX = tmax',round(t[0][1],2)),
('Game-day association','Regress total daily netTotal on gameDay with an intercept. Report the slope to two decimals.',f'{g[0][1]:.2f} dollars. n={len(y)}; p={g[1][1]:.4g}; R²={g[2]:.4f}.','In a binary-predictor regression with an intercept, the slope is the mean outcome for group 1 minus the mean for group 0.','Y = daily SUM(netTotal)\nX = gameDay (1 = game, 0 = no game)',round(g[0][1],2)),
('Interpret an interaction','In sales = b0 + b1 × prior_sales + b2 × gameDay + b3 × prior_sales × gameDay, what is the slope of prior_sales on a game day?','b1 + b3. The slope on a non-game day is b1.','Including two predictors without their product term does not estimate this interaction.','',None),
('Forecast information','Why should a seven-day-ahead forecast not use the realised temperature seven days ahead as if it were known today?','It uses future information unavailable at the forecast date. Use an available weather forecast or a stated temperature scenario and explain uncertainty.','Only information available at prediction time belongs in an honest forecast.','',None)
]:add('Regression','Restaurant',title,prompt,ans,method,rule,['data.xlsm'],code,num)
(D/'questions.json').write_text(json.dumps(Q,indent=2,ensure_ascii=False))
(D/'validation.json').write_text(json.dumps(dict(questions=len(Q),nyc_records=n,nyc_shooting_records=len(shoot),restaurant_dates=len(dates),temperature=t,game_day=g),indent=2))
print('Built',len(Q),'questions; categories:',collections.Counter(q['topic'] for q in Q))
print('NYC categories',collections.Counter(r['Category'] for r in shoot))
print('Regression',t,g)
