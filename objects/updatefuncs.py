#LIBRARIES
import pandas as pd

#FUNCTIONS
def gs_to_df(g_sheet, g_workbook):
    df = pd.DataFrame(g_workbook.worksheet(g_sheet).get_all_records())
    df.set_index(df.columns[0], inplace = True)
    return df

def update_gs_workbook(workbook, sheet_name, df):
    dataframe = df.reset_index()
    worksheet = workbook.worksheet(sheet_name)
    df_formatted = [dataframe.columns.values.tolist()] + dataframe.values.tolist()
    worksheet.update(df_formatted)