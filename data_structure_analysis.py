# import pandas as pd
# import numpy as np
# from ydata_profiling import ProfileReport
# import datetime
#
# # Create a complex dataset
# np.random.seed(42)
# n_samples = 1000
#
# # Generate sample data
# data = {
#     # Numerical columns
#     'user_id': range(1, n_samples + 1),
#     'age': np.random.normal(35, 10, n_samples).round(),
#     'salary': np.random.lognormal(10.5, 0.5, n_samples).round(2),
#     'spending_score': np.random.uniform(0, 100, n_samples).round(2),
#
#     # Categorical columns
#     'education': np.random.choice(['High School', 'Bachelor', 'Master', 'PhD'], n_samples),
#     'occupation': np.random.choice(['Engineer', 'Doctor', 'Teacher', 'Business', 'Other'], n_samples),
#     'marital_status': np.random.choice(['Single', 'Married', 'Divorced'], n_samples),
#
#     # Boolean column
#     'has_credit_card': np.random.choice([True, False], n_samples, p=[0.7, 0.3]),
#
#     # Dates
#     'registration_date': [datetime.datetime.now() - datetime.timedelta(days=int(x)) for x in
#                           np.random.randint(0, 1000, n_samples)],
#
#     # Text column with varying lengths
#     'comments': [f"Customer feedback {i}" * np.random.randint(1, 5) for i in range(n_samples)]
# }
#
# # Create DataFrame
# df = pd.DataFrame(data)
#
# # Add some missing values
# for col in df.columns[1:]:  # Skip user_id
#     mask = np.random.random(n_samples) < 0.05  # 5% missing values
#     df.loc[mask, col] = np.nan
#
# # Add some correlations
# df['credit_score'] = (df['age'] * 10 + df['salary'] / 1000 + np.random.normal(0, 20, n_samples)).round()
#
# import io
# import pandas as pd
#
# import io
# import pandas as pd
#
#
# def get_df_overview(df):
#     buffer = io.StringIO()
#
#     # General info
#     df.info(buf=buffer)
#
#     # Add numeric summary
#     buffer.write("\n\nNumeric Summary:\n")
#     buffer.write(df.describe().to_string())
#
#     # Add correlation matrix only for numeric columns
#     numeric_df = df.select_dtypes(include=['int64', 'float64'])
#     if len(numeric_df.columns) > 1:
#         buffer.write("\n\nCorrelations:\n")
#         buffer.write(numeric_df.corr().round(2).to_string())
#
#     return buffer.getvalue()
#
#
# # Use it
# print(get_df_overview(df))

