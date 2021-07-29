import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(page_title='Covid-19 Dashboard', layout="wide")

d1, d2, d3 = st.beta_columns((3))
navigation = d1.selectbox('Navigation', ['Vaccination Statistics', 'Regional Overview', 'Country Level Overview'])

mapping = {'European Union': 'Europe', 'South Korea':'Korea, South',
           'Cape Verde':'Cabo Verde', 'Congo':'Congo (Kinshasa)',
          'Democratic Republic of Congo':'Congo (Brazzaville)', 'Myanmar':'Burma',
          'Palestine':'Palestinian territories','Taiwan':'Taiwan*','Timor':'Timor-Leste',
          'United States':'US'}

@st.cache(ttl=60*60*1)
def read_data():
    caseURL = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series"    
    vaccineURL = "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/vaccinations/vaccinations.csv"
    url_confirmed = f"{caseURL}/time_series_covid19_confirmed_global.csv"
    url_deaths = f"{caseURL}/time_series_covid19_deaths_global.csv"
    url_recovered = f"{caseURL}/time_series_covid19_recovered_global.csv"

    confirmed = pd.read_csv(url_confirmed, index_col=1)
    confirmed.drop(['Province/State','Lat', 'Long'], axis=1, inplace=True)
    
    deaths = pd.read_csv(url_deaths, index_col=1)
    deaths.drop(['Province/State','Lat', 'Long'], axis=1, inplace=True)
    
    recovered = pd.read_csv(url_recovered, index_col=1)
    recovered.drop(['Province/State','Lat', 'Long'], axis=1, inplace=True)

    confirmed = confirmed.groupby("Country/Region").sum()
    deaths = deaths.groupby("Country/Region").sum()
    recovered = recovered.groupby("Country/Region").sum()
    
    region = pd.read_csv('region.csv',  encoding='latin-1', index_col=0)

    vaccine = pd.read_csv(vaccineURL, parse_dates=['date'])
    vaccine.drop('iso_code', axis=1, inplace=True)
    vaccine['location'].replace(mapping, inplace=True)

    confirmed = pd.merge(confirmed, region, how='left', left_index=True, right_index=True)
    deaths = pd.merge(deaths, region, how='left', left_index=True, right_index=True)
    recovered = pd.merge(recovered, region, how='left', left_index=True, right_index=True)
    vaccine = pd.merge(vaccine, region, how='left', left_on='location', right_index=True)

    return (confirmed, deaths, recovered, vaccine)

def transform(df, collabel='confirmed'):
    df.reset_index(inplace=True)
    df.drop(['Region', 'Continent'], axis=1, inplace=True)
    dfm = pd.melt(df, id_vars=["Country/Region"])
    dfm["date"] = pd.to_datetime(dfm.variable, infer_datetime_format=True)
    dfm = dfm.set_index("date")
    dfm = dfm[["Country/Region","value"]]
    dfm.columns = ["country", collabel]
    return dfm

def main():
	if navigation == 'Regional Overview':
		confirmed, deaths, recovered, vaccine = read_data()
		
		header = st.empty()
		narrative = st.empty()
		geo = confirmed[['Continent','Region']].reset_index()
		
		continent = d2.selectbox('Continent', ['Asia', 'Europe', 'Africa', 'Americas', 'Oceania'])
		region = d3.selectbox('Region', geo[geo.Continent.isin([continent])]['Region'].unique())
		filtered_countries = geo[geo['Region'].isin([region])]['Country/Region'].unique().tolist()
		multiselection = st.multiselect("Select countries:", filtered_countries, default=filtered_countries)
		header.header(f'COVID-19 in {region}')
		narrative.markdown(f"""
		        These are the reported cases for countries in {region}: """
		        f""" {', '.join(filtered_countries)}). """
		        """
		        You can select/ deselect countries and switch between linear and log scales.
		        """)

		logscale = st.checkbox("Log scale", False)
		scale = alt.Scale(type='linear')

		# safeguard for empty selection 
		if len(multiselection) == 0:
		    return 

		b1, b2, b3 = st.beta_columns(3)
		a1, a2 = st.beta_columns((4,2))

		confirmed = confirmed[confirmed.index.isin(multiselection)]
		confirmed = transform(confirmed, collabel="confirmed")

		deaths = deaths[deaths.index.isin(multiselection)]
		deaths = transform(deaths, collabel="deaths")

		recovered = recovered[recovered.index.isin(multiselection)]
		recovered = transform(recovered, collabel="recovered")

		merged = confirmed.merge(deaths, on=['date', 'country'])
		merged = merged.merge(recovered, on=['date', 'country'])
		merged = merged[merged['country'].isin(multiselection)]
		merged['active'] = merged.confirmed - merged.deaths - merged.recovered

		regional = merged[['active', 'recovered', 'deaths']].groupby(merged.index).sum()
		regional.reset_index(inplace=True)
		regional = pd.melt(regional, id_vars=['date'])

		if logscale:
		    scale = alt.Scale(type='log', domain=[1, int(max(confirmed.confirmed))], clamp=True)
		    confirmed['confirmed'] += 0.00001
		    deaths['deaths'] += 0.00001
		    recovered['recovered'] += 0.00001
		    merged['active'] += 0.00001

		c1 = alt.Chart(confirmed.reset_index(), title='Confirmed Cases').properties(height=300).mark_line().encode(
		        x=alt.X("date:T", title="Date"),
		        y=alt.Y("confirmed:Q", title="Cases", scale=scale),
		        color=alt.Color('country:N', title="Country", legend=None),
		        tooltip=[alt.Tooltip('date:T'), alt.Tooltip('confirmed:Q', format=',.0f'), alt.Tooltip('country:N')]
		    )

		c2 = alt.Chart(deaths.reset_index(), title='Death Cases').properties(height=300).mark_line().encode(
		        x=alt.X("date:T", title="Date"),
		        y=alt.Y("deaths:Q", title="Cases", scale=scale),
		        color=alt.Color('country:N', title="Country", legend=None),
		        tooltip=[alt.Tooltip('date:T'), alt.Tooltip('deaths:Q', format=',.0f'), alt.Tooltip('country:N')]
		    )

		c3 = alt.Chart(recovered.reset_index(), title='Recovered Cases').properties(height=300).mark_line().encode(
		        x=alt.X("date:T", title="Date"),
		        y=alt.Y("recovered:Q", title="Cases", scale=scale),
		        color=alt.Color('country:N', title="Country", legend=None),
		        tooltip=[alt.Tooltip('date:T'), alt.Tooltip('recovered:Q', format=',.0f'), alt.Tooltip('country:N')]
		    )

		c4 = alt.Chart(merged.reset_index(), title='Active Cases').properties(height=350).mark_line().encode(
		        x=alt.X("date:T", title="Date"),
		        y=alt.Y("active:Q", title="Cases", scale=scale),
		        color=alt.Color('country:N', title="Country"), #legend=alt.Legend(orient='bottom')
		        tooltip=[alt.Tooltip('date:T'), alt.Tooltip('active:Q', format=',.0f'), alt.Tooltip('country:N')]
		    )

		c5 = alt.Chart(regional, title='Cumulative Cases').properties(height=350).mark_bar().encode(
		        x=alt.X("date:T", title="Date"),
		        y=alt.Y("value:Q", title="Cases", scale=scale),
		        color=alt.Color('variable:N', title="Status", legend=alt.Legend(orient='bottom')),
		        tooltip=[alt.Tooltip('date:T'), alt.Tooltip('value:Q', format=',.0f'), alt.Tooltip('variable:N')]
		    ).configure_range(category={'scheme': 'set1'})

		b1.altair_chart(c1, use_container_width=True)
		b2.altair_chart(c2, use_container_width=True)
		b3.altair_chart(c3, use_container_width=True)
		a1.altair_chart(c4, use_container_width=True)
		a2.altair_chart(c5, use_container_width=True)

	elif navigation == 'Country Level Overview':
		st.header("Per-Country Case statistics")
		subtitle = st.empty()
		w1, w2, _, _ = st.beta_columns(4)
		
		confirmed, deaths, recovered, vaccine = read_data()
		header = st.empty()
		narrative = st.empty()
		geo = confirmed[['Continent','Region']].reset_index()
		
		continent = d2.selectbox('Continent', ['Asia', 'Europe', 'Africa', 'Americas', 'Oceania', 'Others'])
		region = d3.selectbox('Region', geo[geo.Continent.isin([continent])]['Region'].unique())
		filtered_countries = geo[geo['Region'].isin([region])]['Country/Region'].unique().tolist()
		selection = w1.selectbox("Select a country:", filtered_countries, index=0)

		confirmed = confirmed[confirmed.index.isin([selection])]
		confirmed = transform(confirmed, collabel="confirmed")

		deaths = deaths[deaths.index.isin([selection])]
		deaths = transform(deaths, collabel="deaths")

		recovered = recovered[recovered.index.isin([selection])]
		recovered = transform(recovered, collabel="recovered")

		merged = confirmed.merge(deaths, on=['date', 'country'])
		merged = merged.merge(recovered, on=['date', 'country'])
		merged['active'] = merged.confirmed - merged.deaths - merged.recovered

		merged['frate'] = (merged['deaths']/merged['confirmed'])*100
		regional = merged[['active', 'recovered', 'deaths']].groupby(merged.index).sum()
		regional.reset_index(inplace=True)
		regional = pd.melt(regional, id_vars=['date'])

		subtitle.markdown("""
		        These are the reported cases for"""
		        f""" **{selection}** as of **{np.max(confirmed.index.date)}**. """
		        """
		        You can select a country from the dropdown and switch between *linear* and *log* scales.
		        """)

		a1, a2, a3, a4, a5 = st.beta_columns(5)
		a1.warning(f'Confirmed: {np.max(confirmed.confirmed):,} (+{int(confirmed.confirmed.diff().loc[confirmed.index.max()]):,})')
		a2.warning(f'Active: {merged.tail(1).active.values[0]:,} ({int(merged.active.diff().loc[merged.index.max()]):,})')
		a3.error(f'Death: {np.max(deaths.deaths):,} (+{int(deaths.deaths.diff().loc[deaths.index.max()]):,})')
		a4.success(f'Recovered: {np.max(recovered.recovered):,} (+{int(recovered.recovered.diff().loc[recovered.index.max()]):,})')
		a5.error(f'Fatality Rate: {merged.loc[np.max(merged.index)].frate: 0.2f} %')
		logscale = st.checkbox("Log scale", False)
		scale = alt.Scale(type='linear')

		if logscale:
		    scale = alt.Scale(type='log', domain=[1, int(max(confirmed.confirmed))], clamp=True)

		c1 = alt.Chart(regional, title=f'Cumulative Cases in the {selection}').properties(height=350).mark_bar().encode(
		        x=alt.X("date:T", title="Date"),
		        y=alt.Y("value:Q", title="Cases", scale=scale),
		        color=alt.Color('variable:N', title="Status", legend=alt.Legend(orient='bottom')),
		        tooltip=[alt.Tooltip('date:T'), alt.Tooltip('value:Q', format=',.0f'), alt.Tooltip('variable:N')]
		    ).configure_range(category={'scheme': 'set1'})

		c2 = alt.Chart(merged.reset_index(), title=f'Active Cases in the {selection}').properties(height=300).mark_bar().encode(
		        x=alt.X("date:T", title="Date"),
		        y=alt.Y("active:Q", title="Cases", scale=scale),
		        color=alt.Color('country:N', title="Country", legend=None),
		        tooltip=[alt.Tooltip('date:T'), alt.Tooltip('active:Q', format=',.0f')]
		    )

		rm_7day = merged[['active']].rolling('7D').mean()
		c_7day = alt.Chart(rm_7day.reset_index()).properties(height=300).mark_line(strokeDash=[1,1], color='red').encode(
	                x=alt.X("date:T", title="Date"),
	                y=alt.Y("active:Q", scale=scale)	                
	                )

		c3 = alt.Chart(merged.loc['2020-04':].reset_index(), title=f'Fatality Rate in the {selection}').properties(height=300).mark_line().encode(
		        x=alt.X("date:T", title="Date"),
		        y=alt.Y("frate:Q", title="Fatality Rate (%)", scale=scale),
		        color=alt.Color('country:N', title="Country", legend=None),
		        tooltip=[alt.Tooltip('date:T'), alt.Tooltip('frate:Q', format=',.2f')]
		    )
		st.altair_chart(c1, use_container_width=True)
		ch1, ch2 = st.beta_columns(2)
		ch1.altair_chart(c3, use_container_width=True)
		ch2.altair_chart((c2 + c_7day), use_container_width=True)

		st.markdown(f"""
			#### *Summary*:
			_**{selection}** reported {int(confirmed.confirmed.diff().loc[confirmed.index.max()]):,} new cases on **{np.max(confirmed.index.date)}**. This
			constitutes {confirmed.confirmed.diff().loc[confirmed.index.max()]/np.max(confirmed.confirmed)*100:,.2f}% of the total number of confirmed
			cases in the country. There are an additional {int(deaths.deaths.diff().loc[deaths.index.max()]):,} confirmed deaths due to COVID-19, for a total
			of {np.max(deaths.deaths):,}. There are {int(recovered.recovered.diff().loc[recovered.index.max()]):,} recoveries recorded as of date for a total of
			{np.max(recovered.recovered):,}. Active cases stands at {merged.tail(1).active.values[0]:,}._
			""")
	else:

		st.header("COVID-19 Vaccination Statistics Per-Country")
		subtitle = st.empty()
		w1, w2, _, _ = st.beta_columns((12,6,1,1))
		
		confirmed, deaths, recovered, vaccine = read_data()
		header = st.empty()
		narrative = st.empty()

		geo = confirmed[['Continent','Region']].reset_index()
		
		continent = d2.selectbox('Continent', ['Asia', 'Europe', 'Africa', 'Americas', 'Oceania', 'Others'])
		region = d3.selectbox('Region', geo[geo.Continent.isin([continent])]['Region'].unique())
		filtered_countries = geo[geo['Region'].isin([region])]['Country/Region'].unique().tolist()
		# selection = w1.selectbox("Select a country", filtered_countries, index=0)
		filtered_countries = geo[geo['Region'].isin([region])]['Country/Region'].unique().tolist()
		multiselection = w1.multiselect("Select countries:", filtered_countries, default=filtered_countries)
		
		vaccine_variable = {'Total Vaccinations':'total_vaccinations', 'People Vaccinated':'people_vaccinated',
							       'People Fully Vaccinated':'people_fully_vaccinated', 'Daily Vaccinations (Raw)':'daily_vaccinations_raw',
							       'Daily Vaccinations':'daily_vaccinations', 'Total Vaccinations per Hundred':'total_vaccinations_per_hundred',
							       'People Vaccinated per Hundred':'people_vaccinated_per_hundred', 'People Fully Vaccinated per Hundred':'people_fully_vaccinated_per_hundred',
							       'Daily Vaccinations per million':'daily_vaccinations_per_million'}

		varselect = w2.selectbox('Select Variable', list(vaccine_variable.keys()))
		income_df = vaccine[vaccine.location.isin(['High income', 'Low income', 'Lower middle income', 'Upper middle income'])]
		income_df = pd.melt(income_df, id_vars=['location', 'date'])
		income_df["date"] = pd.to_datetime(income_df.date, infer_datetime_format=True)
		
		# a1, a2, a3, a4, a5 = st.beta_columns(5)
		vaccine = pd.melt(vaccine, id_vars=['location', 'date', 'Region', 'Continent'])
		vaccine.dropna(inplace=True)
		# vaccine
		logscale = st.checkbox("Log scale", False)
		scale = alt.Scale(type='linear')
		percontinent = vaccine.groupby(['date','Continent','variable']).sum().reset_index()
		# percontinent.dropna(inplace=True)
		ch1, ch2 = st.beta_columns(2)

		c3 = alt.Chart(percontinent[(percontinent.variable.isin([vaccine_variable[varselect]]))], title=f'{varselect} by Continent').mark_line().encode(
		    x=alt.X('date:T', title='Date'), 
		    y=alt.Y('value:Q', title='Count', scale=scale),
		    color=alt.Color('Continent:N', title='Class', legend=None),
		    tooltip=[alt.Tooltip('date:T'), alt.Tooltip('value:Q', format=',.0f'), alt.Tooltip('Continent:N')])

		if logscale:
			scale = alt.Scale(type='log', domain=[1, int(max(vaccine[vaccine.variable==vaccine_variable[varselect]].value))], clamp=True)

		c1 = alt.Chart(income_df[(income_df.variable.isin([vaccine_variable[varselect]]))], title=f'{varselect} by Income Class').mark_line().encode(
		    x=alt.X('date:T', title='Date'), 
		    y=alt.Y('value:Q', title='Count', scale=scale),
		    color=alt.Color('location:N', title='Class', legend=None),
		    tooltip=[alt.Tooltip('date:T'), alt.Tooltip('value:Q', format=',.0f'), alt.Tooltip('location:N')])

		if len(multiselection) == 0:
			return 

		c2 = alt.Chart(vaccine[(vaccine.location.isin(multiselection)) & (vaccine.variable.isin([vaccine_variable[varselect]]))], title=f'{varselect} in {region}').properties(height=400).mark_line().encode(
			x=alt.X('date:T', title='Date'), 
			y=alt.Y('value:Q', title='Count', scale=scale),
			color=alt.Color('location:N', title='Country'),
			tooltip=[alt.Tooltip('date:T'), alt.Tooltip('value:Q', format=',.0f'), alt.Tooltip('location:N')])
		
		st.altair_chart(c2, use_container_width=True)
		# ch2.altair_chart(c3, use_container_width=True)

	st.info("""\
	    This webapp is heavily inspired by C. Werner's [COVID-19 app](https://www.github.com/cwerner/covid19)     
	    Created by: K. Quisado [Github](https://github.com/kenquix/sea-covid)  
	    Data source: [Johns Hopkins Univerity (GitHub)](https://github.com/CSSEGISandData/COVID-19)""")

if __name__ == '__main__':
	main()