# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Royal Stats is a desktop application designed to track and analyze poker tournament statistics for a single player (Hero). It specializes in tracking tournament performance and knockout statistics for Battle Royale/PKO (Progressive Knockout) poker tournaments.

The application parses poker hand history files and tournament summaries to extract key metrics and provide statistical insights for the player's performance, with a special focus on final table play and knockouts achieved.

## Setup and Running

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py

# Run tests
python -m unittest discover tests
```

## Key Features and Functionality

- **Tournament Tracking**: Records key tournament information including buy-ins, payouts, finishing positions, and knockout counts
- **Final Table Analysis**: Specialized tracking of final table performance (9-max tables)
- **Knockout Statistics**: Detailed tracking of knockouts, including early final table KOs and "big knockouts" (valuable bounties)
- **Session Management**: Groups tournaments into sessions for period-based analysis
- **Statistics Dashboard**: Provides aggregate statistics across all tournaments or filtered by session
- **Place Distribution**: Visualizes final table finishing positions (1-9)
- **Database Management**: Supports multiple SQLite databases for data organization

## Architecture and Components

The application follows a layered architecture with clear separation of concerns:

### 1. UI Layer (`ui/` directory)
- PyQt6-based desktop interface with dark theme by default
- Main window and various views/dialogs
- Components for visualization and data presentation

### 2. Application Logic (`application_service.py`)
- Coordinates between UI, parsers, and database operations
- Handles the core business logic of the application
- Manages the data flow between components

### 3. Parsers (`parsers/` directory)
- `tournament_summary.py` - Parses tournament summary files
- `hand_history.py` - Parses poker hand history files
- Extract relevant information from text files in GG Poker format

### 4. Database Layer (`db/` directory)
- SQLite database with repositories for different entities
- Schema defined in `db/schema.py`
- Repositories for each entity type in `db/repositories/`

### 5. Statistics Modules (`stats/` directory)
- Various statistics calculations (ROI, knockouts, etc.)
- Each module implements statistics for specific metrics
- Pluggable architecture for extending functionality

### 6. Models (`models/` directory)
- Data models representing entities like tournaments and sessions

## Database Schema

The SQLite database includes the following tables:
- `sessions`: Records of import sessions
- `tournaments`: Tournament data and results
- `hero_final_table_hands`: Detailed information about hands played at final tables
- `overall_stats`: Aggregate statistics across all tournaments
- `places_distribution`: Distribution of final table finishes by position
- `stat_modules`: Configuration for statistics modules

## Specific Requirements and Definitions

- **Hero**: The player whose statistics are being tracked
- **Final Table Definition**: 9-max table with blinds ≥ 50/100
- **Early Final Table Stage**: Defined as the 9-6 player stage of the final table
- **Knockout Detection Logic**:
  - Player is considered knocked out by Hero if:
    - They went all-in
    - Hero had them covered (Hero's stack ≥ their stack)
    - Hero won the pot to which they contributed
- **Big Knockouts**: Valuable bounties categorized by their size relative to buy-in (1.5x, 2x, 10x, 100x, 1000x, 10000x)

## Key Configuration

Configuration settings are in `config.py`, which includes:
- Hero player name
- Database path settings
- Final table and knockout zone parameters
- UI configuration (dark theme by default)

## Data Processing Pipeline

1. Parse hand histories first to identify knockouts and final table data
2. Parse tournament summaries to gather finishing positions and payouts
3. Merge data and calculate statistics
4. Store results in the database
5. Present statistics through the UI

## Common Development Tasks

### Add a New Statistic Module

1. Create a new class in the `stats/` directory that extends `stats/base.py`
2. Implement the required methods for calculating and displaying statistics
3. Update the UI to display the new statistic

### Add or Modify Database Schema

1. Update the schema in `db/schema.py`
2. Create or update the corresponding repository in `db/repositories/`
3. Create or update the model in `models/`
4. Ensure the schema changes are applied to new and existing databases

### Extend the Parser

1. Update relevant parser implementations in `parsers/` directory
2. Add tests for new parsing logic
3. Ensure backwards compatibility with existing hand history formats

### Add UI Components

1. Create new components in the `ui/` directory
2. Follow the existing design patterns and UI conventions
3. Connect the new components to the appropriate data sources