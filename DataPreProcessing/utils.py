import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os


sns.set(style='darkgrid')
plt.rcParams.update({
    # 'font.sans-serif': 'Comic Sans MS',
    #'font.family': 'serif'
})

def Read_Multiple_Files(directory, fileFormat):
    dfs = []
    for file in os.listdir(directory):
        if file.endswith(fileFormat):
            file_path = os.path.join(directory, file)
            df = pd.read_csv(file_path, low_memory= False)
            columns_to_rename = {'NODATA':f'NODATA_{os.path.splitext(file)[0]}', 'TOT_NODATA':f'TOT_NODATA_{os.path.splitext(file)[0]}', 'ACC_NODATA':f'ACC_NODATA_{os.path.splitext(file)[0]}', 'CAT_NODATA':f'CAT_NODATA_{os.path.splitext(file)[0]}'}
            for col in columns_to_rename:
                if col in df.columns:
                    df.rename(columns={col: columns_to_rename[col]}, inplace=True)
            dfs.append(df) 
    return dfs

def Merge_Multiple_Files(dfs, on_what):
    Indep_var_reache = dfs[0]
    for df in dfs[1:len(dfs)]: 
        Indep_var_reache = pd.merge(Indep_var_reache, df, how="left", on=on_what)
    return Indep_var_reache

def closest(lst, K):
    return lst[min(range(len(lst)), key = lambda i: abs(lst[i]-K))]


def IQR(df):
    q1_w= pd.DataFrame(df).quantile(0.25)[0] #Q1
    q3_w= pd.DataFrame(df).quantile(0.75)[0] #Q3
    iqr_w= q3_w - q1_w #IQR
    fence_low_w = q1_w - (1.5*iqr_w) #Lower limit
    fence_high_w = q3_w + (1.5*iqr_w) #Upper limit
    return fence_low_w, fence_high_w


def scatterPlot_Type1(df, df_bnk, df_mf, usgs_cd):
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), constrained_layout=True)
    Dep_var_after_filtration_v = df[df["site_no"] == usgs_cd]
    df_bnk_v = df_bnk[df_bnk["site_no"] == usgs_cd]
    df_mf_v = df_mf[df_mf["site_no"] == usgs_cd]
    threshold = df_bnk_v['q_va_bnk']
    df_over_bnk = Dep_var_after_filtration_v[(Dep_var_after_filtration_v['q_va'] > threshold.iloc[0])]
    df_within_bnk= Dep_var_after_filtration_v[(Dep_var_after_filtration_v['q_va'] < threshold.iloc[0])]
    axes[0].scatter(df_within_bnk["stream_wdth_va"], df_within_bnk["mean_depth_va"], s=200, color='#264653', alpha=0.7, edgecolors='k')
    axes[0].scatter(df_over_bnk["stream_wdth_va"], df_over_bnk["mean_depth_va"], s=200, color='#264653', alpha=0.15, edgecolors='k')
    axes[0].scatter(df_bnk_v["stream_wdth_va_bnk"], df_bnk_v["mean_depth_va_bnk"], s=400, color='mediumvioletred', edgecolors='w', marker='P')
    axes[0].scatter(df_mf_v["stream_wdth_va_mf"], df_mf_v["mean_depth_va_mf"], s=350, color='#dc7633', edgecolors='w', marker='X')
    axes[0].set_xlabel('Width (m)', fontsize=22)
    axes[0].set_ylabel('Mean Depth (m)', fontsize=22)
    axes[0].tick_params(labelsize=20)
    axes[0].set_facecolor("#F0F0F0") 
    axes[1].scatter(df_within_bnk["q_va"], df_within_bnk["q8_stream_width_D_mean_depth"], s=200, color='#264653', alpha=0.7, edgecolors='k')
    axes[1].scatter(df_over_bnk["q_va"], df_over_bnk["q8_stream_width_D_mean_depth"], s=200, color='#264653', alpha=0.15, edgecolors='k')
    axes[1].scatter(df_bnk_v["q_va_bnk"], df_bnk_v["q8_stream_width_D_mean_depth_bnk"], s=400, color='mediumvioletred', edgecolors='w', marker='P')
    axes[1].scatter(df_mf_v["q_va_mf"], df_mf_v["q8_stream_width_D_mean_depth_mf"], s=350, color='#dc7633', edgecolors='w', marker='X')
    axes[1].set_xlabel('Discharge (cms)', fontsize=22)
    axes[1].set_ylabel('\n Width/Mean Depth (m/m)', fontsize=22)
    axes[1].set_facecolor("#F0F0F0")
    axes[1].tick_params(labelsize=20)
    axes[1].legend(["Within channel" , "Overbank", "Bankfull", "Mean-flow"], title=False, facecolor = "w", fontsize=20, loc='lower center', bbox_to_anchor=(1.25,0.35), ncol=1 , columnspacing=0.8, handletextpad=0.3, handlelength=0.8)
    fig.text(0.43, 1.05, f"\n USGS site number 0{usgs_cd}", ha='center', size=26)
    plt.show()

def HYDRoSWOTUnitsConvertor(df):
    M_df= pd.DataFrame()
    M_df['host']= df['host']   #dimensionless
    M_df['agency_cd']= df['agency_cd']   #code
    M_df['site_no']= df['site_no']   #dimensionless
    M_df['station_nm']= df['station_nm']   #dimensionless
    M_df['dec_lat_va']= df['dec_lat_va']   #degrees
    M_df['dec_long_va']= df['dec_long_va']   #degrees
    M_df['coord_datum_cd']= df['coord_datum_cd']   #degrees
    M_df['drain_area_va']= df['drain_area_va']*2.58999999   #square mile to square kilometers
    M_df['contrib_drain_area_va']= df['contrib_drain_area_va']*2.58999999   #square mile to square kilometers
    M_df['alt_va']= df['alt_va']*0.3048   #feet to meter
    M_df['alt_datum_cd']= df['alt_datum_cd']   #code
    M_df['site_tp_cd']= df['site_tp_cd']   #code
    M_df['ad_site_cd']= df['ad_site_cd']   #code
    M_df['site_visit_start_dt']= df['site_visit_start_dt']   #time
    M_df['site_visit_start_dt_sg']= df['site_visit_start_dt_sg']   #code
    M_df['data_aging_cd']= df['data_aging_cd']   #code
    M_df['q_meas_no']= df['q_meas_no']   #dimensionless
    M_df['q_meas_dt']= df['q_meas_dt']   #time
    M_df['q_meas_td']= df['q_meas_td']   #date and time
    M_df['q_va']= df['q_va']*0.028316801   #cubic feet per second to cubic meter per second
    M_df['stage_va']= df['stage_va']*0.3048   #feet to meter
    M_df['stage_diff_va']= df['stage_diff_va']*0.3048   #feet to meter
    M_df['stage_diff_du']= df['stage_diff_du']   #second
    M_df['mean_idx_vel_va']= df['mean_idx_vel_va']*0.3048   #feet per second to meter per second
    M_df['std_sec_area_va']= df['std_sec_area_va']*0.092903   #Square feet to square meter
    M_df['std_sec_vel_va']= df['std_sec_vel_va']*0.3048   #feet per second to meter per second
    M_df['q_adj_va']= df['q_adj_va']*0.028316801   #cubic feet per second to cubic meter per second
    M_df['base_flw_cd']= df['base_flw_cd']   #code
    M_df['q_meas_qual_cd']= df['q_meas_qual_cd']   #code
    M_df['q_meas_used_fg']= df['q_meas_used_fg']   #Y equals Yes; N equals No
    M_df['q_meas_chan_nu']= df['q_meas_chan_nu']   #dimensionless
    M_df['stream_wdth_va']= df['stream_wdth_va']*0.3048   #feet to meter
    M_df['xsec_area_va']= df['xsec_area_va']*0.092903   #Square feet to square meter
    M_df['mean_vel_va']= df['mean_vel_va']*0.3048   #feet per second to meter per second
    M_df['max_vel_va']= df['max_vel_va']*0.3048   #feet per second to meter per second
    M_df['q_coef_var_va']= df['q_coef_var_va']   #dimensionless
    M_df['flw_meas_fc']= df['flw_meas_fc']   #percent
    M_df['mean_depth_va']= df['mean_depth_va']*0.3048   #feet to meter
    M_df['max_depth_va']= df['max_depth_va']*0.3048   #feet to meter
    M_df['adcp_freq_cd']= df['adcp_freq_cd']   #code
    M_df['q_meas_type_cd']= df['q_meas_type_cd']   #code
    M_df['q_meth_cd']= df['q_meth_cd']   #code
    M_df['vel_meth_cd']= df['vel_meth_cd']   #code
    M_df['meas_q_va']= df['meas_q_va']*0.028316801   #cubic feet per second to cubic meter per second
    M_df['chan_stability_cd']= df['chan_stability_cd']   #code
    M_df['chan_mat_cd']= df['chan_mat_cd']   #code
    M_df['vel_dstrb_cd']= df['vel_dstrb_cd']   #code
    M_df['vert_vel_dstrb_cd']= df['vert_vel_dstrb_cd']   #code
    M_df['q1_Percent_va']= df['q1_Percent_va']   #percent
    M_df['q1_Outside5Percent']= df['q1_Outside5Percent']   #-1 indicates a + or - 5 percent exceedance
    M_df['q2_xsec_area_X_mean_vel_va']= df['q2_xsec_area_X_mean_vel_va']*0.028316801   #cubic feet per second to cubic meter per second
    M_df['q2_Percent_q_va']= df['q2_Percent_q_va']   #percent
    M_df['q2_q_va_OutsideBounds']= df['q2_q_va_OutsideBounds']   #-1 indicates a + or - 5 percent exceedance
    M_df['q2_Percent_meas_q_va']= df['q2_Percent_meas_q_va']   #percent
    M_df['q2_meas_q_va_OutsideBounds']= df['q2_meas_q_va_OutsideBounds']   #-1 indicates a + or - 5 percent exceedance
    M_df['q3_CalcQ']= df['q3_CalcQ']*0.028316801   #cubic feet per second to cubic meter per second
    M_df['q3_PercentCalcQ_q_va']= df['q3_PercentCalcQ_q_va']   #percent
    M_df['q3_q_va_OutsideBounds']= df['q3_q_va_OutsideBounds']   #-1 indicates a + or - 5 percent exceedance
    M_df['q3_PercentCalcQ_meas_q_va']= df['q3_PercentCalcQ_meas_q_va']   #percent
    M_df['q3_meas_q_va_OutsideBounds']= df['q3_meas_q_va_OutsideBounds']   #-1 indicates a + or - 5 percent exceedance
    M_df['q4_xsec_area_D_stream_width']= df['q4_xsec_area_D_stream_width']*0.3048   #feet to meter
    M_df['q4_Percent_xsec_area_D_stream_width']= df['q4_Percent_xsec_area_D_stream_width']   #percent
    M_df['q4_OutsideBounds']= df['q4_OutsideBounds']   #-1 indicates a + or - 5 percent exceedance
    M_df['q5_Mean_GT_Max']= df['q5_Mean_GT_Max']   #-1 indicates mean depth greater than max depth
    M_df['q6_mean_vel_GT_max_vel']= df['q6_mean_vel_GT_max_vel']   #-1 indicates mean velocity greater than max velocity
    M_df['q6_JRatio']= df['q6_JRatio']   #dimensionless
    M_df['q6_JRatioGTo582']= df['q6_JRatioGTo582']   #-1 indicates q6_JRatio greater than 0.582
    M_df['q6_JRatioLTo836']= df['q6_JRatioLTo836']   #-1 indicates q6_JRatio less than 0.836
    M_df['q7_max_vel_D_mean_vel']= df['q7_max_vel_D_mean_vel']   #dimensionless
    M_df['q7_max_vel_D_mean_vel_LT2']= df['q7_max_vel_D_mean_vel_LT2']  #-1 indicates that the ratio of max to mean velocity is less than 2
    M_df['q8_stream_width_D_mean_depth']= df['q8_stream_width_D_mean_depth']   #dimensionless
    M_df['q8_GT2']= df['q8_GT2']   #-1 indicates that the ratio of stream width to mean depth is greater than 2
    M_df['q8_LT200']= df['q8_LT200']   #-1 indicates that the ratio of stream width to mean depth is less than 200
    M_df['q9_stream_width_GT100']= df['q9_stream_width_GT100']   #-1 indicates stream width is greater than 100
    M_df['q10_mean_vel_GTo5']= df['q10_mean_vel_GTo5']   #-1 indicates mean velocity is greater than 0.5
    return M_df

def NHDPlusUnitsConvertor(df):
    df["QA_cms"] = df["QA_MA"]* 0.028316801 #convert cfs to cms
    df["QC_cms"] = df["QC_MA"]* 0.028316801 #convert cfs to cms
    df["QE_cms"] = df["QE_MA"]* 0.028316801 #convert cfs to cms
    return df


