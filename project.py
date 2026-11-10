"""
CSC271H1 Final Project 
project.py

Functions for loading, cleaning, storing, querying and visualizing
U.S. Presidential and Senate election data (1976-2020)

Author: Arshad Saleh
"""

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# Section 1: Database Helper Functions

def create_database(db_name:str) -> None:
    """Create a new SQLite file named db_name.

    Parameters:
        db_name (str): The filename for the new SQLite database.
    """ 
    conn = sqlite3.connect(db_name)
    conn.close()

def connect(db_name: str) -> sqlite3.Connection:
    """Return a connection to the SQLite database.

    Parameters:
        db_name (str): The filename for the new SQLite database.

    Returns:
        sqlite3.Connection: An open connection to the database.
    """

    conn = sqlite3.connect(db_name)
    return conn

def run_sql(conn: sqlite3.Connection, sql: str,
            params:tuple | dict | None = None) -> pd.DataFrame | None:
    """Run the SQL statement, sql, using connection, conn.

    Parameters:
        conn (sqlite3.Connection): An open connection to the database.
        sql (str): The SQL query to be executed.
        params (tuple or dict or None): Parameters for 
        paramaterized queries. (Optional)

    Returns:
        pd.DataFrame or None: The query returns a DataFrame for SELECT
        statemens, else returns None.
    """
    if sql.strip().upper().startswith("SELECT"):
        return pd.read_sql_query(sql, conn, params=params)
    else:
        if params is None:
            conn.execute(sql)
        else:
            conn.execute(sql, params)
        conn.commit()
        return None
    
def add_dataframe(conn: sqlite3.Connection,
                  df: pd.DataFrame,
                  table_name: str) -> None:
    """Load a DataFrame into a database table and replace it already
    if it exists.

    Parameters:
        conn (sqlite3.Connection): An open connection to the database.
        df (pd.DataFrame): The DataFrame to load into the database.
        table_name (str): The name of the table to create in the database.
    """
    df.to_sql(table_name, conn, if_exists='replace', index=False)

# Section 2: Load and Clean Data

def load_senate_data(filepath: str) -> pd.DataFrame:
    """
    Load and clean the U.S. Senate election dataset.
    Keeps only general elections (stage = 'gen'), 
    non-special elections (special=False), Democrat and Republican
    candidates and excludes the 2021 election year. Adds an 
    election_type column ('presidential' or 'midterm') 
    based on the year.

    Parameters:
        filepath (str): Path to the Senate data CSV file.

    Returns: 
        pd.DataFrame: Cleaned Senate DataFrame with columns:
        year, state, candidate, party_simplified, candidatevotes, 
        totalvotes, special and election_type.
    """
    df = pd.read_csv(filepath)

    # Keep only the general elections, non-special, major parties and exclude 2021
    df = df[df['stage'] == 'gen']
    df = df[df['special'] == False]
    df = df[df['party_simplified'].isin(['DEMOCRAT', 'REPUBLICAN'])]
    df = df[df['year'] != 2021]

    # Keep only needed columns
    df = df[['year', 'state', 'candidate', 'party_simplified',
            'candidatevotes', 'totalvotes', 'special']]
    
    #Add election_type
    pres_years = [1976, 1980, 1984, 1988, 1992, 1996, 2000, 2004,
                  2008, 2012, 2016, 2020]
    df['election_type'] = 'midterm'
    df['election_type'][df['year'].isin(pres_years)] = 'presidential'

    return df

def load_president_data(filepath: str) -> pd.DataFrame:
    """Load and clean the U.S. presidential election dataset.
    Keeping only Democrat and Republican candidates and removes write-ins
    
    Parameters:
        filepath (str): Path to the Senate data CSV file.
    
    Returns:
         pd.DataFrame: Cleaned Presidential DataFrame with columns:
        year, state, candidate, party_simplified, candidatevotes, 
        totalvotes.
    """
    df = pd.read_csv(filepath)

    # Keep only major parties and remove write-ins
    df = df[df['party_simplified'].isin(['DEMOCRAT', 'REPUBLICAN'])]
    df = df[df['writein'] == False]

    # Keep only the columns that are needed
    df = df[['year', 'state', 'candidate', 'party_simplified', 
             'candidatevotes', 'totalvotes']]
    
    return df

# Section 3: SQL Queries

def query_senate_seats_won(conn: sqlite3.Connection) -> pd.DataFrame:
    """Query 1: GROUP BY and COUNT: Senate seats won per party per year.
    Finds the winner of each state race for each election year and then
    counts how many seats each party won. 

    Parameters:
        conn (sqlite3.Connection): An open connection to the database.
    
    Returns:
        pd.DataFrame: columns that are year, party_simplified, seats_won 
        and election_type.
    """
    sql = """
        SELECT
            year,
            party_simplified,
            COUNT(*) AS seats_won,
            election_type
        FROM(
            SELECT
                year,
                state,
                party_simplified,
                election_type,
                MAX(candidatevotes) AS max_votes
            FROM senate_elections
            GROUP BY year, state
        )
        GROUP BY year, party_simplified
        ORDER BY year, party_simplified
    """
    return run_sql(conn, sql)

def query_coattail_effect(conn: sqlite3.Connection) -> pd.DataFrame:
    """Query 2: JOIN, GROUP BY, SUM: 
    Presidential vote share vs. Senate seats won 
    This joins the presidential and senate tables on year and party, 
    only looking at presidential election years and computes the national
    presidential vote share and senate seats won per party per year.

    Parameters:
        conn (sqlite3.Connection): An open connection to the database.

    Returns:
        pd.DataFrame: columns that are year, party_simplified, pres_vote_share
        and senate_seats_won.
    """
    sql = """
        SELECT
            p.year,
            p.party_simplified,
            ROUND(
                CAST(SUM(p.candidatevotes) AS FLOAT) / 
                CAST(SUM(p.totalvotes) AS FLOAT) * 100,
                2
            ) AS pres_vote_share,
            s.senate_seats_won
            FROM president_elections p
            JOIN (
                SELECT 
                    year,
                    party_simplified,
                    COUNT(*) AS senate_seats_won
                FROM (
                    SELECT year, state, party_simplified, MAX(candidatevotes)
                    FROM senate_elections
                    WHERE election_type = 'presidential'
                    GROUP BY year, state
                )
                GROUP BY year, party_simplified
            ) s
            ON p.year = s.year AND p.party_simplified = s.party_simplified
            GROUP BY p.year, p.party_simplified
            ORDER BY p.year, p.party_simplified
    """
    return run_sql(conn, sql)

def query_net_seat_change_by_party(conn: sqlite3.Connection,
                                   party: str) -> pd.DataFrame:
    """Query 3: Parameterized - Senate seats and net change for a given party.
    This counts the Senate seats won by the party each year and then computes
    the net change compared to the previous year. 
    
    Parameters:
        conn (sqlite3.Connection): An open connection to the database.
        party (str): The party filtered by 'DEMOCRAT' or 'REPUBLICAN'.

    Returns:
        pd.DataFrame: columns that are year, party_simplified, election_type
        seats_won, net_seat_change.
    """
    sql = """
        SELECT
            year,
            party_simplified,
            seats_won,
            election_type
        FROM (
            SELECT
                year,
                party_simplified,
                COUNT(*) AS seats_won,
                election_type
            FROM (
                SELECT year, state, party_simplified, election_type,
                        MAX(candidatevotes)
                FROM senate_elections
                GROUP BY year, state
            )
            WHERE party_simplified = ?
            GROUP BY year, party_simplified
        )
        ORDER BY year
        """
    df = run_sql(conn, sql, params=(party,))
    df['net_seat_change'] = df['seats_won'].diff()
    return df

# Section 4: Derived Data Helper

def compute_net_seat_change(seats_df: pd.DataFrame) -> pd.DataFrame:
    """Compute net Senate seat change for both parties.
    Uses the output of query_senate_seats_won and computes the change
    in seats won compared to the previous election year,
    computed separately for each party using groupby and diff.

    Parameters:
    seats_df (pd.DataFrame): Result of query_senate_seats_won with the 
    column year, party_simplified, seats_won, election_type.

    Returns:
    pd.DataFrame: Same columns input with net_seat_change added.
    """
    df = seats_df.copy().sort_values(['party_simplified', 'year'])
    df['net_seat_change'] = df.groupby('party_simplified')['seats_won'].diff()
    return df

# Section 5: Data Visualization

def plot_seats_won_by_election_type(seats_df: pd.DataFrame) -> None:
    """Plot 1: Bar Chart for Average Senate seats won by party and election type.
    This compares average seats won by Democarts and Republicans in presidential 
    years vs. midterm years.

    Parameters:
    seats_df (pd.DataFrame): Result of query_senate_seats_won with the 
    column year, party_simplified, seats_won, election_type.
    """
    average = (
        seats_df.groupby(['election_type', 'party_simplified'])['seats_won']
        .mean()
        .reset_index()
    )
    
    pivot = average.pivot(index='election_type',
                          columns='party_simplified',
                          values='seats_won')
    
    fig, ax = plt.subplots(figsize=(8, 5))
    pivot.plot(kind='bar', ax=ax, color=['steelblue', 'firebrick'])
    ax.set_xlabel('Election Type')
    ax.set_ylabel('Average Senate Seats Won')
    ax.set_title('Average Senate Seats Won by Party and Election Type (1976 - 2020)')
    ax.legend()
    plt.tight_layout()
    plt.show()

def plot_coattail_effect(coattail_df: pd.DataFrame) -> None:
    """Plot 2: Scatter Plot for Presidential vote share vs. Senate seats won.
    Each point on the scatter plot represents one party in one presidential year.
    
    Parameters:
    coattail_df (pd.DataFrame): Results of query_coattail_effect with columns
    year, party_simplified, pres_vote_share, senate_seats_won
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    democrat = coattail_df[coattail_df['party_simplified'] == 'DEMOCRAT']
    republican = coattail_df[coattail_df['party_simplified'] == 'REPUBLICAN']

    democrat.plot(kind='scatter', x='pres_vote_share', y='senate_seats_won',
                  ax=ax, color='steelblue', label='Democrat')
    republican.plot(kind='scatter', x='pres_vote_share', y='senate_seats_won',
                  ax=ax, color='firebrick', label='Republican')
    
    ax.set_xlabel('Presidential Vote Share (%)')
    ax.set_ylabel('Senate Seats Won')
    ax.set_title('Presidential Vote Share vs. Senate Seats Won (1976-2020)')
    ax.legend()
    plt.tight_layout()
    plt.show()

def plot_net_seat_change_per_cycle(net_df: pd.DataFrame) -> None:
    """Plot 3: Line Plot for Net Senate seat change per cycle by party.
    Shows how each party gains and loses Senate seats per cycle.

    Parameters:
    net_df (pd.DataFrame): Results of compute_net_seat_change with columns
    year, party_simplified, seats_won, election_type, net_seat_change.
    """
    df = net_df[net_df['net_seat_change'].isna() == False]

    democrat = df[df['party_simplified'] == 'DEMOCRAT'].sort_values('year')
    republican = df[df['party_simplified'] == 'REPUBLICAN'].sort_values('year')

    fig, ax = plt.subplots(figsize=(12, 5))

    democrat.plot(x='year', y='net_seat_change', ax=ax,
                  marker='o', linestyle='-', color='steelblue', label='Democrat')
    republican.plot(x='year', y='net_seat_change', ax=ax,
                  marker='o', linestyle='-', color='firebrick', label='Republican')
    
    ax.set_xlabel('Year')
    ax.set_ylabel('Net Senate Seat Change')
    ax.set_title('Net Senate Seat Change Per Cycle by Party (1978-2020)')
    ax.legend()
    plt.tight_layout()
    plt.show()