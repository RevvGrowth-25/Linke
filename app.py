import streamlit as st
import pandas as pd
import requests
import re
import time
import random
from urllib.parse import urlparse
from io import StringIO

# Try importing google search module
try:
    from googlesearch import search
except ImportError:
    st.error(
        "Error: 'google' package not found. Please install it using 'pip install google' or 'pip install google-search-results'")

# Set page configuration
st.set_page_config(
    page_title="LinkedIn Automation Tool",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to improve appearance
st.markdown("""
<style>
    .main {
        background-color: #f9f9f9;
    }
    .stButton button {
        background-color: #0A66C2;
        color: white;
        font-weight: bold;
        border-radius: 4px;
        padding: 0.5rem 1rem;
        border: none;
    }
    .stButton button:hover {
        background-color: #084d92;
    }
    .success-message {
        color: #1e8e3e;
        font-weight: bold;
        padding: 10px;
        border-radius: 4px;
        background-color: #e6f4ea;
    }
    .error-message {
        color: #d93025;
        font-weight: bold;
        padding: 10px;
        border-radius: 4px;
        background-color: #fce8e6;
    }
    .warning-message {
        color: #ea8600;
        font-weight: bold;
        padding: 10px;
        border-radius: 4px;
        background-color: #fef7e0;
    }
    .info-box {
        background-color: #e8f0fe;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
    }
    h1, h2, h3 {
        color: #0A66C2;
    }
    .stProgress > div > div > div > div {
        background-color: #0A66C2;
    }
</style>
""", unsafe_allow_html=True)


# ========== PROFILE FINDER FUNCTIONS ==========

def search_linkedin_profiles(keyword, description, num_results=10):
    """
    Search for LinkedIn profiles related to a keyword and description.

    Args:
        keyword (str): The main topic to search for (e.g., job title, skill)
        description (str): Additional context to narrow the search (e.g., industry, location)
        num_results (int): Maximum number of results to return

    Returns:
        list: List of LinkedIn profile URLs
    """
    # Define queries specifically targeting user profiles
    queries = [
        f'site:linkedin.com/in "{keyword}" "{description}"',
        f'inurl:linkedin.com/in "{keyword}" "{description}"',
        f'site:linkedin.com/in intitle:"{keyword}" "{description}"'
    ]

    profile_urls = []
    profile_pattern = re.compile(r'(https?://.*?linkedin\.com/in/[^/\s]+)/?(?:\s|$)')

    status_placeholder = st.empty()
    status_placeholder.info(f"Searching for LinkedIn profiles matching: {keyword} - {description}")

    progress_bar = st.progress(0)
    log_container = st.empty()
    log_text = "Search Progress:\n"

    for i, query in enumerate(queries):
        try:
            log_text += f"\nRunning query {i + 1}/{len(queries)}: {query}\n"
            log_container.text_area("Search Log", log_text, height=200)

            # Update progress
            progress_bar.progress((i) / len(queries) * 0.5)

            search_results = list(search(query, num=10, stop=10))
            for j, url in enumerate(search_results):
                # Extract only profile URLs using regex
                matches = profile_pattern.findall(url)
                if matches:
                    profile_url = matches[0]
                    if profile_url not in profile_urls:
                        profile_urls.append(profile_url)
                        log_text += f"Found profile: {profile_url}\n"
                        log_container.text_area("Search Log", log_text, height=200)

                        if len(profile_urls) >= num_results:
                            log_text += f"\nReached maximum number of results ({num_results}).\n"
                            log_container.text_area("Search Log", log_text, height=200)
                            progress_bar.progress(1.0)
                            return profile_urls

                # Update search progress
                sub_progress = (i + (j + 1) / len(search_results)) / len(queries) * 0.5
                progress_bar.progress(min(0.5 + sub_progress, 0.9))

                # Add a small delay to avoid getting blocked
                time.sleep(random.uniform(0.5, 1.5))

        except Exception as e:
            log_text += f"Error during search with query {i + 1}: {str(e)}\n"
            log_container.text_area("Search Log", log_text, height=200)
            # Continue with next query if one fails
            continue

    # If few results found, try with broader search
    if len(profile_urls) < num_results:
        log_text += "\nTrying broader search...\n"
        log_container.text_area("Search Log", log_text, height=200)

        try:
            broader_query = f'site:linkedin.com/in "{keyword}"'
            log_text += f"Broader query: {broader_query}\n"
            log_container.text_area("Search Log", log_text, height=200)

            search_results = list(search(broader_query, num=10, stop=10))
            for j, url in enumerate(search_results):
                matches = profile_pattern.findall(url)
                if matches:
                    profile_url = matches[0]
                    if profile_url not in profile_urls:
                        profile_urls.append(profile_url)
                        log_text += f"Found profile: {profile_url}\n"
                        log_container.text_area("Search Log", log_text, height=200)

                        if len(profile_urls) >= num_results:
                            break

                # Update progress bar
                progress_bar.progress(min(0.9 + (j + 1) / len(search_results) * 0.1, 0.99))
                time.sleep(random.uniform(0.5, 1.5))

        except Exception as e:
            log_text += f"Error in broader search: {str(e)}\n"
            log_container.text_area("Search Log", log_text, height=200)

    if not profile_urls:
        log_text += "\nNo profiles found matching your criteria.\n"
    else:
        log_text += f"\nSearch completed. Found {len(profile_urls)} profiles.\n"

    log_container.text_area("Search Log", log_text, height=200)
    progress_bar.progress(1.0)

    return profile_urls


# ========== OUTREACH MANAGER FUNCTIONS ==========

def extract_linkedin_username(url):
    """Extract the username from a LinkedIn URL."""
    # Handle different URL formats
    if not url or not isinstance(url, str):
        return None

    # Parse URL to get path
    try:
        parsed = urlparse(url.strip())
        path = parsed.path

        # Extract username using regex
        match = re.search(r'/in/([^/]+)', path)
        if match:
            return match.group(1)
    except Exception:
        return None

    return None


def extract_job_title(username, api_key, dsn, account_id):
    """Extract job title from LinkedIn profile if available."""
    url = f"https://{dsn}/api/v1/users/{username}"

    headers = {
        "X-API-KEY": api_key,
        "accept": "application/json"
    }

    params = {
        "linkedin_sections": "*",
        "account_id": account_id
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        # Try to extract job title from profile data
        headline = data.get("headline", "")
        experience = data.get("experience", [])

        if experience and len(experience) > 0 and "title" in experience[0]:
            return experience[0]["title"]
        elif headline:
            return headline
        else:
            return "Professional"

    except:
        return "Professional"


def get_user_provider_id(username, api_key, dsn, account_id):
    """Get the provider_id for a LinkedIn user."""
    url = f"https://{dsn}/api/v1/users/{username}"

    headers = {
        "X-API-KEY": api_key,
        "accept": "application/json"
    }

    params = {
        "linkedin_sections": "*",
        "account_id": account_id
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        # Extract provider_id from response
        provider_id = data.get("provider_id")

        if not provider_id:
            return None, "Could not find provider_id in the response"

        return provider_id, None

    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, 'response') and e.response:
            error_msg = f"{error_msg}: {e.response.text}"
        return None, error_msg


def send_message(provider_id, message_text, api_key, dsn, account_id):
    """Attempt to send a message to the LinkedIn user."""
    url = f"https://{dsn}/api/v1/chats"

    headers = {
        "X-API-KEY": api_key,
        "accept": "application/json"
    }

    payload = {
        "account_id": account_id,
        "text": message_text,
        "attendees_ids": provider_id
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        return True, "Message sent successfully"

    except requests.exceptions.RequestException as e:
        # Check if the error indicates we're not connected
        if hasattr(e, 'response') and e.response:
            if e.response.status_code == 400 or e.response.status_code == 403:
                return False, f"Failed to send message: {e.response.text}"
        return False, f"Error sending message: {str(e)}"


def send_connection_request(provider_id, message, api_key, dsn, account_id):
    """Send a connection request to the LinkedIn user using the invite endpoint."""
    url = f"https://{dsn}/api/v1/users/invite"

    headers = {
        "X-API-KEY": api_key,
        "accept": "application/json",
        "content-type": "application/json"
    }

    payload = {
        "provider_id": provider_id,
        "account_id": account_id,
        "message": message
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return True, "Connection request sent successfully"

    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, 'response') and e.response:
            error_msg = f"{error_msg}: {e.response.text}"
        return False, f"Error sending connection request: {error_msg}"


def process_linkedin_profile(linkedin_url, message_template, connection_template, api_key, dsn, account_id,
                             personalize=True):
    """Process a single LinkedIn profile URL with personalized messages."""
    result = {
        "url": linkedin_url,
        "username": None,
        "job_title": None,
        "provider_id": None,
        "action": None,
        "status": None,
        "error": None
    }

    # Step 1: Extract username from URL
    username = extract_linkedin_username(linkedin_url)
    if not username:
        result["error"] = f"Could not extract username from URL: {linkedin_url}"
        result["status"] = "Failed"
        return result

    result["username"] = username

    # Step 2: Get provider_id for the user
    provider_id, error = get_user_provider_id(username, api_key, dsn, account_id)
    if error:
        result["error"] = error
        result["status"] = "Failed"
        return result

    result["provider_id"] = provider_id

    # Step 3: Extract job title for personalization if enabled
    if personalize:
        job_title = extract_job_title(username, api_key, dsn, account_id)
        result["job_title"] = job_title

        # Personalize messages
        personalized_message = message_template.replace("{name}", username.capitalize())
        personalized_message = personalized_message.replace("{job_title}", job_title)

        personalized_connection = connection_template.replace("{name}", username.capitalize())
        personalized_connection = personalized_connection.replace("{job_title}", job_title)
    else:
        personalized_message = message_template
        personalized_connection = connection_template

    # Step 4: Try to send a message
    message_success, message_result = send_message(provider_id, personalized_message, api_key, dsn, account_id)

    if message_success:
        result["action"] = "Message"
        result["status"] = "Success"
        return result

    # Step 5: If message fails, send a connection request
    connect_success, connect_result = send_connection_request(provider_id, personalized_connection, api_key, dsn,
                                                              account_id)

    if connect_success:
        result["action"] = "Connection Request"
        result["status"] = "Success"
    else:
        result["action"] = "Connection Request"
        result["status"] = "Failed"
        result["error"] = connect_result

    return result


# ========== MAIN APP ==========

def main():
    st.title("LinkedIn Automation Tool")

    with st.sidebar:
        st.image("https://brandlogos.net/wp-content/uploads/2016/06/linkedin-logo-512x512.png", width=100)
        st.header("API Configuration")

        api_key = st.text_input("Unipile API Key", type="password")
        dsn = st.text_input("DSN (Domain)", value="api.unipile.com")
        account_id = st.text_input("Account ID", value="")

        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        This app allows you to:
        - Find LinkedIn profiles based on keywords
        - Process multiple LinkedIn profiles at once
        - Send personalized messages to connections
        - Send connection requests when messaging fails
        - Track the status of all interactions
        """)

    # Main content area tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Profile Finder", "Outreach Manager", "Results Dashboard", "Settings & Help"])

    with tab1:
        st.header("LinkedIn Profile Finder")
        st.markdown("""
        Find LinkedIn profiles based on keywords and descriptions. This tool uses Google search to find 
        profiles that match your criteria.
        """)

        col1, col2, col3 = st.columns(3)

        with col1:
            keyword = st.text_input("Enter keyword (job title, skill, etc.):", placeholder="Software Engineer")

        with col2:
            description = st.text_input("Enter description (industry, location, etc.):",
                                        placeholder="AI startup San Francisco")

        with col3:
            num_results = st.number_input("Maximum results:", min_value=1, max_value=50, value=10)

        find_button = st.button("Find LinkedIn Profiles")

        if find_button:
            if not keyword:
                st.error("Please enter a keyword to search for")
            else:
                # Create a container for search results
                st.markdown("### Search Results")

                # Perform the search
                profiles = search_linkedin_profiles(keyword, description, num_results)

                # Store results in session state
                if profiles:
                    st.session_state['found_profiles'] = profiles

                    # Display results in a table
                    df = pd.DataFrame({
                        "Profile URL": profiles,
                        "Username": [extract_linkedin_username(url) for url in profiles]
                    })

                    st.dataframe(df)

                    # Allow saving to CSV
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "Download Results as CSV",
                        csv,
                        "linkedin_profiles.csv",
                        "text/csv",
                        key='download-finder-csv'
                    )

                    st.success(f"Found {len(profiles)} LinkedIn profiles matching your criteria!")
                    st.info("You can now go to the Outreach Manager tab to start your outreach campaign.")
                else:
                    st.warning(
                        "No profiles found matching your criteria. Try different keywords or a broader description.")

    with tab2:
        st.header("LinkedIn Outreach Manager")

        # Message templates
        st.subheader("Message Templates")

        personalize = st.checkbox("Personalize messages with name and job title", value=True)
        st.markdown("""
        Use `{name}` and `{job_title}` as placeholders in your templates to personalize messages.
        Example: "Hi {name}, I noticed you're a {job_title} and wanted to connect..."
        """)

        col1, col2 = st.columns(2)

        with col1:
            message_text = st.text_area(
                "Message template (for connections):",
                value="Hi {name}! I noticed you're a {job_title} and I'm interested in connecting to discuss potential collaborations in this field.",
                height=150
            )

        with col2:
            connection_text = st.text_area(
                "Connection request template:",
                value="Hi {name}! I'm reaching out as we're both in the {job_title} space. I'd love to add you to my professional network on LinkedIn.",
                height=150
            )

        st.markdown("---")
        st.subheader("LinkedIn Profiles")

        # Tabs for different input methods
        input_tab1, input_tab2, input_tab3 = st.tabs(["Use Found Profiles", "Manual Entry", "Upload CSV"])

        linkedin_urls = []

        with input_tab1:
            if 'found_profiles' in st.session_state and st.session_state['found_profiles']:
                st.success(f"Found {len(st.session_state['found_profiles'])} profiles from your search!")

                # Show preview
                for i, url in enumerate(st.session_state['found_profiles'][:5], 1):
                    st.text(f"{i}. {url}")

                if len(st.session_state['found_profiles']) > 5:
                    st.text(f"... and {len(st.session_state['found_profiles']) - 5} more")

                use_found = st.checkbox("Use these profiles for outreach", value=True)
                if use_found:
                    linkedin_urls = st.session_state['found_profiles']
            else:
                st.info("No profiles found yet. Go to the Profile Finder tab to search for LinkedIn profiles.")

        with input_tab2:
            urls_input = st.text_area(
                "Enter LinkedIn profile URLs (one per line):",
                height=150,
                help="Example: https://www.linkedin.com/in/username"
            )

            if urls_input:
                manual_urls = [url.strip() for url in urls_input.strip().split('\n') if url.strip()]
                if manual_urls:
                    linkedin_urls.extend(manual_urls)

        with input_tab3:
            uploaded_file = st.file_uploader(
                "Upload CSV file with LinkedIn URLs",
                type=["csv"],
                help="CSV should have a column named 'linkedin_url'"
            )

            if uploaded_file is not None:
                try:
                    df = pd.read_csv(uploaded_file)
                    if 'linkedin_url' in df.columns:
                        csv_urls = df['linkedin_url'].dropna().tolist()
                        linkedin_urls.extend(csv_urls)
                    else:
                        st.error("CSV file must contain a column named 'linkedin_url'")
                except Exception as e:
                    st.error(f"Error reading CSV file: {str(e)}")

        # Show preview of URLs to be processed
        if linkedin_urls:
            st.success(f"Total: {len(linkedin_urls)} LinkedIn profile URLs to process")

            with st.expander("Preview URLs"):
                for i, url in enumerate(linkedin_urls[:10], 1):
                    st.text(f"{i}. {url}")

                if len(linkedin_urls) > 10:
                    st.text(f"... and {len(linkedin_urls) - 10} more")

        # Process button
        process_button = st.button("Process LinkedIn Profiles")

        # Validate inputs and process
        if process_button:
            if not api_key:
                st.error("Please enter your Unipile API Key")
            elif not account_id:
                st.error("Please enter your Account ID")
            elif not linkedin_urls:
                st.error("Please enter at least one LinkedIn profile URL")
            else:
                # Process the URLs
                results = []
                progress_bar = st.progress(0)
                status_text = st.empty()

                for i, url in enumerate(linkedin_urls):
                    status_text.text(f"Processing {i + 1}/{len(linkedin_urls)}: {url}")
                    result = process_linkedin_profile(
                        url, message_text, connection_text, api_key, dsn, account_id, personalize
                    )
                    results.append(result)
                    progress_bar.progress((i + 1) / len(linkedin_urls))
                    # Add a small delay to avoid API rate limits
                    time.sleep(0.5)

                status_text.text("Processing complete!")

                # Store results in session state for the dashboard
                st.session_state['processing_results'] = results

                # Summary of results
                success_count = sum(1 for r in results if r["status"] == "Success")
                message_count = sum(1 for r in results if r["action"] == "Message" and r["status"] == "Success")
                connection_count = sum(
                    1 for r in results if r["action"] == "Connection Request" and r["status"] == "Success")

                st.markdown("### Processing Summary")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Processed", len(results))
                col2.metric("Success Rate", f"{success_count / len(results):.0%}")
                col3.metric("Messages Sent", message_count)
                col4.metric("Connection Requests", connection_count)

                st.markdown("See the 'Results Dashboard' tab for detailed results.")

    with tab3:
        st.header("Results Dashboard")

        if 'processing_results' in st.session_state and st.session_state['processing_results']:
            results = st.session_state['processing_results']

            # Convert to DataFrame for easier filtering and display
            results_df = pd.DataFrame(results)

            # Filter options
            st.subheader("Filter Results")
            col1, col2, col3 = st.columns(3)

            with col1:
                status_filter = st.multiselect(
                    "Status",
                    options=["Success", "Failed"],
                    default=["Success", "Failed"]
                )

            with col2:
                action_filter = st.multiselect(
                    "Action",
                    options=["Message", "Connection Request", None],
                    default=["Message", "Connection Request", None]
                )

            with col3:
                search_term = st.text_input("Search by Username")

            # Apply filters
            filtered_df = results_df
            if status_filter:
                filtered_df = filtered_df[filtered_df['status'].isin(status_filter)]
            if action_filter:
                filtered_df = filtered_df[filtered_df['action'].isin(action_filter)]
            if search_term:
                filtered_df = filtered_df[filtered_df['username'].str.contains(search_term, na=False, case=False)]

            # Download button for results
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                "Download Results as CSV",
                csv,
                "linkedin_outreach_results.csv",
                "text/csv",
                key='download-csv'
            )

            # Display results
            st.markdown(f"### Showing {len(filtered_df)} of {len(results_df)} results")

            for _, row in filtered_df.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])

                    with col1:
                        st.markdown(f"**{row['username'] or 'Unknown User'}**")
                        if row.get('job_title'):
                            st.markdown(f"Job: {row['job_title']}")
                        st.markdown(f"URL: {row['url']}")
                        if row['provider_id']:
                            st.markdown(f"Provider ID: {row['provider_id']}")

                    with col2:
                        action = row['action'] or "Not Processed"
                        st.markdown(f"Action: **{action}**")
                        if row['error']:
                            st.markdown(f"Error: {row['error']}")

                    with col3:
                        if row['status'] == "Success":
                            st.markdown('<div class="success-message">✅ Success</div>', unsafe_allow_html=True)
                        elif row['status'] == "Failed":
                            st.markdown('<div class="error-message">❌ Failed</div>', unsafe_allow_html=True)
                        else:
                            st.markdown('<div class="warning-message">⚠️ Unknown</div>', unsafe_allow_html=True)

                    st.markdown("---")
        else:
            st.info("No processing results available. Process some LinkedIn profiles to see results here.")

    with tab4:
        st.header("Settings & Help")

        with st.expander("How to Use This App"):
            st.markdown("""
            ### Quick Start Guide

            1. **Find LinkedIn Profiles**
               - Go to the "Profile Finder" tab
               - Enter keywords and description 
               - Click "Find LinkedIn Profiles"

            2. **Prepare Your Outreach**
               - Go to the "Outreach Manager" tab
               - Customize your message templates
               - Use the found profiles or add your own

            3. **Process Profiles**
               - Enter your API credentials in the sidebar
               - Click "Process LinkedIn Profiles"
               - Monitor progress in real-time

            4. **Analyze Results**
               - Check the "Results Dashboard" tab
               - Filter and sort results
               - Download CSV reports for your records
            """)

        with st.expander("FAQ"):
            st.markdown("""
            ### Frequently Asked Questions

            **Q: What is the difference between messages and connection requests?**  
            A: Messages can only be sent to users you're already connected with. For users you're not connected with, the app automatically sends connection requests.

            **Q: How does the profile finder work?**  
            A: The finder uses Google search with specialized queries to find LinkedIn profiles matching your keywords and descriptions.

            **Q: Is there a limit to how many profiles I can process?**  
            A: While the app doesn't impose limits, the Unipile API may have rate limits. We recommend processing in batches of 50-100 profiles.

            **Q: How do I get API credentials?**  
            A: You need to sign up for a Unipile account and generate API credentials from their dashboard.

            **Q: Can I personalize my messages?**  
            A: Yes! Use the placeholders `{name}` and `{job_title}` in your message templates to automatically personalize each message.
            """)

        with st.expander("Troubleshooting"):
            st.markdown("""
            ### Common Issues and Solutions

            **Profile Finder Issues**
            - If you get few results, try using broader keywords
            - Make sure to use industry-specific terms for better targeting
            - If search fails, you may need to install or upgrade the 'google' package

            **API Authentication Errors**  
            - Double-check your API Key and Account ID
            - Ensure your Unipile account is active and has sufficient permissions

            **Connection Request Failures**  
            - You may have already sent a request to this user
            - There might be LinkedIn restrictions on your account
            - The user's profile might have privacy settings that prevent requests
            """)


if __name__ == "__main__":
    main()
