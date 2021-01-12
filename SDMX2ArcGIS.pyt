# -*- coding: utf-8 -*-

import arcpy
import os
import sys
import requests

def get_sdmx_field_list(in_url):
    response = requests.get(
        in_url 
        #, headers={'accept': 'application/vnd.sdmx.data+json;version=1.0.0-wd'}
    )

    if not response:
        return ['Unable to parse SDMX response. Check URL.']
    else:
        res_json = response.json()
        fields = []
        series_dimensions = res_json['data']['structure']['dimensions']['series']
        for s in series_dimensions:
            fields.append(f'{s["id"]} | (Name)')
            fields.append(f'{s["id"]}_CODE | (ID)')

        return fields

def get_observations(res_json):
    if 'observations' in res_json['data']['dataSets'][0]:
        return res_json['data']['dataSets'][0]['observations']

    if 'series' in res_json['data']['dataSets'][0]:
        return res_json['data']['dataSets'][0]['series']

def query_and_parse_sdmx(in_url, in_headers=None):
    headers = {}
    if in_headers is not None:
        for header in in_headers:
            headers[header[0]] = header[1]

    response = requests.get(in_url, headers=headers)

    if response:
        res_json = response.json()

        series_dimensions = res_json['data']['structure']['dimensions']['series']
        observation_dimensions = res_json['data']['structure']['dimensions']['observation']
        series_attributes = res_json['data']['structure']['attributes']['series']
        observation_attributes = res_json['data']['structure']['attributes']['observation']

        obs = get_observations(res_json)
        res_count = len(obs.keys())

        return {
            'series_dimensions': series_dimensions,
            'observation_dimensions': observation_dimensions,
            'series_attributes': series_attributes,
            'observation_attributes': observation_attributes,
            'obs': obs,
            'res_count': res_count
        }

def get_fields(observation_dimensions, series_dimensions, series_attributes, observation_attributes):
    fields = []
    for dim in series_dimensions:
        name = dim['id']
        alias = dim['name']  
        type = 'TEXT'

        if isinstance(alias, dict) and 'en' in alias:
            alias = alias['en']

        fields.append([ f'{name}_CODE', type , f'{name}_CODE' ])
        fields.append([ f'{name}', type, alias ])

    for dim in observation_dimensions:
        name = dim['id']
        alias = dim['name']
        type = 'TEXT'

        if isinstance(alias, dict) and 'en' in alias:
            alias = alias['en']

        fields.append([ f'{name}_CODE', type, f'{name}_CODE' ])
        fields.append([ f'{name}', type, alias ])

    fields.append([ 'OBS_VALUE', 'DOUBLE', 'Observed Value' ])

    for dim in series_attributes:
        name = dim['id']
        alias = dim['name']
        type = 'TEXT'

        if isinstance(alias, dict) and 'en' in alias:
            alias = alias['en']

        fields.append([ f'{name}_CODE', type, f'{name}_CODE' ])
        fields.append([ f'{name}', type, alias ])

    for dim in observation_attributes:
        name = dim['id']
        alias = dim['name']
        type = 'TEXT'

        if isinstance(alias, dict) and 'en' in alias:
            alias = alias['en']

        fields.append([ f'{name}_CODE', type, f'{name}_CODE' ])
        fields.append([ f'{name}', type, alias ])

    return fields

def convert_sdmx_json_to_feature_rows(sdmx_response, in_sdmxjoinfield, in_sdmxjoinfieldconversion):
    observations = sdmx_response['obs']
    series_dimensions = sdmx_response['series_dimensions']
    series_attributes = sdmx_response['series_attributes']
    observation_dimensions = sdmx_response['observation_dimensions']
    observation_attributes = sdmx_response['observation_attributes']

    fields = get_fields(observation_dimensions, series_dimensions,
                        series_attributes, observation_attributes)
    
    has_added_conversion_field = False
    features = []

    for obs in observations:
        dim_splits = obs.split(':')

        holder = {}
        for i, current_key_str in enumerate(dim_splits):
            current_key_str = int(current_key_str)
            series = [f for f in series_dimensions if f['keyPosition']
                      == i][0]

            series_id = series['id']
            series_fieldname = f'{series_id}_CODE'
            holder[series_fieldname] = series['values'][current_key_str]['id']
            series_id_value = series['values'][current_key_str]['name']
            if isinstance(series_id_value, dict) and 'en' in series_id_value:
                series_id_value = series['values'][current_key_str]['name']['en']

            holder[series_id] = series_id_value

            if series_fieldname == in_sdmxjoinfield and in_sdmxjoinfieldconversion is not None:
                if in_sdmxjoinfieldconversion == 'String':
                    holder[f'{series_fieldname}_str'] = str(series['values'][current_key_str]['id'])
                    if not has_added_conversion_field:
                        fields.append([f'{series_fieldname}_str', 'TEXT'])
                        has_added_conversion_field = True
                else: 
                    holder[f'{series_fieldname}_int'] = int(series['values'][current_key_str]['id'])
                    if not has_added_conversion_field:
                        fields.append([f'{series_fieldname}_int', 'LONG'])
                        has_added_conversion_field = True

            if series_id == in_sdmxjoinfield and in_sdmxjoinfieldconversion is not None:
                if in_sdmxjoinfieldconversion == 'String':
                    holder[f'{series_id}_str'] = str(series['values'][current_key_str]['id'])
                    if not has_added_conversion_field:
                        fields.append([f'{series_id}_str', 'TEXT'])
                        has_added_conversion_field = True
                else: 
                    holder[f'{series_id}_int'] = int(series['values'][current_key_str]['id'])
                    if not has_added_conversion_field:
                        fields.append([f'{series_id}_int', 'LONG'])
                        has_added_conversion_field = True


        attributes_index = None
        if 'attributes' in observations[obs]:
            attributes = observations[obs]['attributes']
            for i, att in enumerate(attributes):
                if att is not None:
                    serie_atts = series_attributes[i]
                    sa_fieldname = serie_atts['id']

                    series_att_values = serie_atts['values'][att]
                    sa_code = series_att_values['id']
                    sa_name_value = series_att_values['name']
                    if isinstance(sa_name_value, dict) and 'en' in sa_name_value:
                        sa_name_value = series_att_values['name']['en']

                    holder[sa_fieldname] = sa_name_value
                    holder[f'{sa_fieldname}_CODE'] = sa_code


        observation_values = observations[obs]['observations']
        for o_value in observation_values:
            feature = {'attributes': {}}

            o_index = int(o_value)
            obs_dim_value = observation_dimensions[0]['values'][o_index]
            obs_dim_field_name = observation_dimensions[0]['id']
            obs_dim_field_name_code = f'{obs_dim_field_name}_CODE'
            feature['attributes'][obs_dim_field_name_code] = obs_dim_value['id']

            obs_name_value = obs_dim_value['name']
            if isinstance(obs_name_value, dict) and 'en' in obs_name_value:
                obs_name_value = obs_dim_value['name']['en']

            feature['attributes'][obs_dim_field_name] = obs_name_value

            values_array = observation_values[o_value]
            obs_value = values_array[0]
            feature['attributes']['OBS_VALUE'] = obs_value

            # first value in `values_array` is the OBS_VALUE
            # next values are referenced from `observation_attributes`
            values_array.pop(0)
            for a, o_value in enumerate(values_array):
                obs_atts = observation_attributes[a]

                obs_atts_id = obs_atts['id']
                obs_atts_id_field = f'{obs_atts_id}_CODE'

                if o_value is None or 'values' not in obs_atts or len(obs_atts['values']) == 0:
                    feature['attributes'][obs_atts_id_field] = None
                    feature['attributes'][obs_atts_id] = None
                    continue

                obs_atts_name_value = obs_atts['values'][o_value]['name']
                if isinstance(obs_atts_name_value, dict) and 'en' in obs_atts_name_value:
                    obs_atts_name_value = obs_atts_name_value['en']

                feature['attributes'][obs_atts_id_field] = obs_atts['values'][o_value]['id']   
                feature['attributes'][obs_atts_id] = obs_atts_name_value

            for h in holder:
                feature['attributes'][h] = holder[h]

            features.append(feature)

    return fields, features

def create_fc_table(in_workspace, output_filename):
    try:
        tbl_output = arcpy.CreateTable_management(in_workspace, output_filename)             
        return tbl_output.getOutput(0)
    except Exception:
        e = sys.exc_info()[1]
        error = e.args[0]
        print (error)
        return error

def add_fields(fields, tbl):
    try:
        arcpy.AddFields_management(tbl, fields)   
    except Exception:
        e = sys.exc_info()[1]
        error = e.args[0]
        print (error)
        return error, None

def add_rows(sdmx_feature_rows, tbl, fields):
    cursor = arcpy.da.InsertCursor(tbl, fields)

    cnt = len(sdmx_feature_rows)
    arcpy.SetProgressor('step', f'Inserting {cnt} rows into output feature class ...', 0, cnt, 1)    
    counter = 1
    for sdmx_row in sdmx_feature_rows:
        row = []
        for f in fields:
            row_value = None
            if f in sdmx_row['attributes']:
                row_value = sdmx_row['attributes'][f] 
            
            row.append(row_value)
        
        arcpy.SetProgressorPosition(counter)
        arcpy.SetProgressorLabel(f'Inserting row {counter} of {cnt} ...')
        try:
            cursor.insertRow(tuple(row))
            counter = counter + 1
        except:
            # arcpy.AddMessage(cursor.fields)
            arcpy.AddError('Error inserting rows')
            del cursor
            return 'Error inserting rows', None

    del cursor


def get_geom(geo_field, geo_value):
    global geom_cache
    global geo_fl

    wc = """{0} = '{1}'""".format(arcpy.AddFieldDelimiters(geo_fl, geo_field), geo_value)
    # arcpy.AddMessage(wc)
    if geo_value in geom_cache:
        # arcpy.AddMessage(f'got from cache for {geo_value}')
        return geom_cache[geo_value]
    else:
        geom = None
        row = None
        try:
            row = next(arcpy.da.SearchCursor(geo_fl, ['SHAPE@', geo_field],where_clause=wc))
        except: 
            pass

        if row and len(row) > 0:
            # arcpy.AddMessage(row)
            geom = row[0]
            geo_val_to_add = row[1]
            geom_cache[geo_val_to_add] = geom
        else:
            arcpy.AddMessage(f'Unable to get geometry from Geography layer. The where_clause, {wc} did not return results.')

        return geom


def join_proper(tbl, fields, in_outworkspace, in_outputtablename, in_sdmxjoinfield, in_geolayer, in_geojoinfield, in_sdmxjoinfieldconversion, in_shouldkeepallgeo, geo_fields_to_delete):

    sdmx_join_field = in_sdmxjoinfield
    if in_sdmxjoinfieldconversion is not None:
        type = 'TEXT'
        field_name = f'{in_sdmxjoinfield}_str'
        expression_func = 'str'
        if in_sdmxjoinfieldconversion == 'Integer':
            type = 'LONG'
            field_name = f'{in_sdmxjoinfield}_int'
            expression_func = 'int'

        arcpy.AddField_management(tbl, field_name, type)

        expression = f'{expression_func}(!{field_name}!)'
        arcpy.CalculateField_management(tbl, field_name, expression, 'PYTHON3')

        sdmx_join_field = field_name

    keep_all = 'KEEP_COMMON'
    if in_shouldkeepallgeo:
        keep_all = 'KEEP_ALL'

    joined_table = arcpy.AddJoin_management(in_geolayer, in_geojoinfield, tbl, sdmx_join_field, keep_all)    

    arcpy.CopyFeatures_management(joined_table, os.path.join(in_outworkspace, in_outputtablename))

    if len(geo_fields_to_delete) > 0:
        geo_layer_title = in_geolayer.name

        fields_deleted = [f'{geo_layer_title}_{f}' for f in geo_fields_to_delete]

        arcpy.DeleteField_management(os.path.join(in_outworkspace, in_outputtablename), fields_deleted)

    try:
        arcpy.RemoveJoin_management(in_geolayer)
    except:
        arcpy.AddWarning('Unable to remove join. Check your geography layer for any Joins that may remain')
    

    return os.path.join(in_outworkspace, in_outputtablename)

def join_to_geo(tbl, fields, in_outworkspace, in_outputtablename, in_sdmxjoinfield, in_geolayer, in_geojoinfield, in_shouldkeepallgeo, unique_location_ids):
    global geo_fl

    try:
        arcpy.MakeFeatureLayer_management(in_geolayer, geo_fl)
    except Exception:
        e = sys.exc_info()[1]
        error = e.args[0]
        print (error)
        return error, None

    in_geo_fl_desc = arcpy.Describe(geo_fl)
    #in_geo_field_info = in_geo_fl_desc.fieldInfo
    geo_layer_feature_type = in_geo_fl_desc.shapeType
    geo_layer_sr = in_geo_fl_desc.spatialReference
    
    try:
        arcpy.CreateFeatureclass_management(in_outworkspace, in_outputtablename, geo_layer_feature_type, '#', '#', '#', geo_layer_sr)
    except Exception:
        e = sys.exc_info()[1]
        error = e.args[0]
        print (error)
        return error, None

    add_fields(fields, os.path.join(in_outworkspace, in_outputtablename))

    out_fields = [f[0] for f in fields]
    insert_rows = []
    with arcpy.da.SearchCursor(tbl, out_fields) as cursor:
        for row in cursor:
            cursor_fields = cursor.fields
            search_val = row[cursor_fields.index(in_sdmxjoinfield)]
            geom = get_geom(in_geojoinfield, search_val)

            row_list = list(row)
            row_list.insert(0, geom)
            insert_row = tuple(row_list)

            insert_rows.append(insert_row)
    
    cnt = int(arcpy.GetCount_management(tbl)[0])
    counter = 1
    arcpy.SetProgressor('step', f'Inserting {cnt} rows into output geo feature class ...', 0, cnt, 1)
    i_cursor = arcpy.da.InsertCursor(os.path.join(in_outworkspace, in_outputtablename), ['SHAPE@'] + out_fields)
    for row in insert_rows:           
        arcpy.SetProgressorPosition(counter)
        arcpy.SetProgressorLabel(f'Inserting row {counter} of {cnt} ...')
        try:
            i_cursor.insertRow(row)
            counter = counter + 1
        except:
            #arcpy.AddMessage(i_cursor.fields)
            arcpy.AddError('Error inserting rows')
            del i_cursor
            return 'Error inserting rows', None
    
    del i_cursor

    return None, os.path.join(in_outworkspace, in_outputtablename)


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "SDMX2ArcGIS"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [SDMXQueryUrlToTable]


class SDMXQueryUrlToTable(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "SDMX API To Feature Class"
        self.description = "Convert an SDMX API Response to a Feature Class"
        self.canRunInBackground = True

    def getParameterInfo(self):
        """Define parameter definitions"""

        #######################
        # START DEFINE PARAMS #
        #######################

        # SDMX API Query Url
        param_url = arcpy.Parameter(
            displayName="SDMX Query Url",
            name="in_url",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        # Keep all Geography Features
        param_useheaders = arcpy.Parameter(
            displayName="Use HTTP Headers",
            name="in_useheaders",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")

        # Keep all Geography Features
        param_headers = arcpy.Parameter(
            displayName="HTTP Headers",
            name="in_headers",
            datatype="GPValueTable",
            parameterType="Optional",
            direction="Input")

        # Output Table Name
        param_outputtablename = arcpy.Parameter(
            displayName="Output Table Name",
            name="in_outputtablename",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        # Output Workspace
        param_outworkspace = arcpy.Parameter(
            displayName="Output Workspace",
            name="in_outputfcworkspace",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

         # Join to Geography
        param_joingeo = arcpy.Parameter(
            displayName="Join to Geography",
            name="in_joingeo",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")

        # SDMX Join Field
        param_sdmxjoinfield = arcpy.Parameter(
            displayName="SDMX Join Field",
            name="in_sdmxjoinfield",
            datatype="String",
            parameterType="Optional",
            direction="Input")

        # SDMX Join Field - Convert to string/integer
        param_sdmxjoinfieldconversions = arcpy.Parameter(
            displayName="Convert SDMX Join Field Values",
            name="in_sdmxjoinfieldconversion",
            datatype="String",
            parameterType="Optional",
            direction="Input")

        # Geography Layer
        param_geolayer = arcpy.Parameter(
            displayName="Geography Layer",
            name="in_geolayer",
            datatype=["GPFeatureLayer", "GPLayer", "Shapefile"],
            parameterType="Optional",
            direction="Input")

        # Geography Join Field
        param_geojoinfield = arcpy.Parameter(
            displayName="Geography Join Field",
            name="in_geofield",
            datatype="Field",
            parameterType="Optional",
            direction="Input")

        # Geography Join Field - Convert to string/integer
        param_geojoinfieldconversions = arcpy.Parameter(
            displayName="Convert to String/Integer",
            name="in_geojoinfieldconversion",
            datatype="String",
            parameterType="Optional",
            direction="Input")

        # Keep all Geography Features
        param_keepallgeo = arcpy.Parameter(
            displayName="Keep all Geography Features",
            name="in_keepallgeo",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")

        # Fields to keep from geography layer
        param_geofieldmapping = arcpy.Parameter(
            displayName="Geography Fields to Keep",
            name="in_geofieldmapping",
            datatype="GPString",
            parameterType="Optional",
            multiValue=True,
            direction="Input")

        # Name of output geography joined layer
        param_outputgeoname =  arcpy.Parameter(
            displayName="Output Feature Class Name",
            name="in_geolayername",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        # output fc path
        param_outputfctablepath = arcpy.Parameter(
            displayName="Output Feature Class",
            name="param_outputfcpath",
            datatype=["GPFeatureLayer","DETable"],
            parameterType="Derived",
            direction="Output")

        # ABS sample
        # param_url.value = 'https://api.data.abs.gov.au/data/ABS,ABS_REGIONAL_ASGS2016,1.0.0/INCOME_17+EQUIV_2.SA2..A?startPeriod=2010&endPeriod=2019&format=jsondata'

        # SDGs sample
        #param_url.value = 'https://data.un.org/ws/rest/data/IAEG-SDGs,DF_SDG_GLH,1.3/..SI_POV_EMP1.1+9+543+62+747+753+15+12+504+729+788+818+90+30+156+410+496+34+50+64+144+356+364+462+524+586+35+104+116+360+418+458+608+626+704+764+143+398+417+762+860+145+31+51+268+275+368+400+422+760+792+887+8+70+112+199+202+24+72+108+120+132+140+148+174+178+180+204+231+242+266+270+288+324+384+404+419+32+68+76+152+170+188+214+218+222+320+332+340+388+426+430+432+450+454+466+478+480+484+498+499+508+516+558+562+566+591+598+600+604+624+643+646+686+688+694+710+716+722+768+800+804+834+854+858+862+894._T+F+M........../ALL/?detail=full&dimensionAtObservation=TIME_PERIOD'
        #param_useheaders.value = True
        
        param_geojoinfield.parameterDependencies = [param_geolayer.name]

        param_headers.columns = [['GPString', 'Header'], ['GPString', 'Value']]
        param_headers.filters[0].type = 'ValueList'
        #param_headers.value = [['accept', 'application/vnd.sdmx.data+json; charset=utf-8; version=1.0.0-wd']]

        param_headers.enabled = False
        param_sdmxjoinfield.enabled = False
        param_geolayer.enabled = False
        param_geojoinfield.enabled = False
        param_geojoinfieldconversions.enabled = False
        param_keepallgeo.enabled = False
        param_geofieldmapping.enabled = False

        param_sdmxjoinfieldconversions.filter.list = ['None', 'String', 'Integer']
        param_geojoinfieldconversions.filter.list = ['None', 'String', 'Integer']

        param_geofieldmapping.filter.type = 'ValueList'
        param_geofieldmapping.filter.list = []

        return [
            param_url,                          # 0
            param_useheaders,                   # 1
            param_headers,                      # 2
            param_outputtablename,              # 3
            param_outworkspace,                 # 4
            param_joingeo,                      # 5
            param_sdmxjoinfield,                # 6
            param_sdmxjoinfieldconversions,     # 7
            param_geolayer,                     # 8
            param_geojoinfield,                 # 9
            param_outputgeoname,                # 10
            param_keepallgeo,                   # 11
            param_geofieldmapping,              # 12
            param_outputfctablepath             # 13
        ]

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if parameters[0].altered and not parameters[0].hasBeenValidated:
            parameters[6].filter.list = []
            fields = get_sdmx_field_list(parameters[0].value)
            if fields:
                parameters[6].filter.list = fields
                parameters[6].value = fields[0]   

        parameters[6].enabled = parameters[5].value
        parameters[7].enabled = parameters[5].value
        parameters[8].enabled = parameters[5].value
        parameters[9].enabled = parameters[5].value
        parameters[10].enabled = parameters[5].value
        parameters[11].enabled = parameters[5].value
        parameters[12].enabled = parameters[5].value

        parameters[2].enabled = parameters[1].value

        if parameters[8].value is not None and parameters[8].altered and not parameters[8].hasBeenValidated:
            desc = arcpy.Describe(parameters[8].value)
            if desc is not None:
                fields = []
                fields = [f.name for f in desc.fields if not f.required and f.type not in ['Geometry', 'OID']]
                parameters[12].value = ''
                parameters[12].filter.list = []
                parameters[12].filter.list = fields

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        global geom_cache
        geom_cache = {}

        global geo_fl
        geo_fl = 'geo_fl'

        in_api_url = parameters[0].valueAsText
        in_useheaders = parameters[1].value
        in_headers = parameters[2].value
        in_outputtablename = parameters[3].valueAsText
        in_outworkspace = parameters[4].valueAsText
        in_shouldjoin = parameters[5].value    
        in_sdmxjoinfield = parameters[6].valueAsText.split('|')[0].strip()
        in_sdmxjoinfieldconversion = parameters[7].valueAsText
        in_geolayer = parameters[8].value
        in_geojoinfield = parameters[9].valueAsText
        in_outputgeoname = parameters[10].valueAsText
        in_shouldkeepallgeo = parameters[11].value
        in_geofieldmapping = parameters[12].value

        if in_sdmxjoinfieldconversion == 'None':
            in_sdmxjoinfieldconversion = None

        # Query the SDMX API
        arcpy.SetProgressor('default', 'Querying the SDMX API ...')
        headers = None
        if in_useheaders:
            headers = in_headers

        sdmx_response = query_and_parse_sdmx(in_api_url, headers)

        # Convert the SDMX Response to features
        arcpy.SetProgressor('default', 'Converting the SDMX response ...')
        fields, sdmx_feature_rows = convert_sdmx_json_to_feature_rows(sdmx_response, in_sdmxjoinfield, in_sdmxjoinfieldconversion)

        # add the fields
        arcpy.SetProgressor('default', 'Creating the feature class table ...')
        tbl = create_fc_table(in_outworkspace, in_outputtablename)
        
        # add the fields
        arcpy.SetProgressor('default', 'Adding fields to output feature class ...')
        add_fields(fields, tbl)

        # Add the rows to the table
        arcpy.SetProgressor('default', 'Adding rows to SDMX feature class table ...')
        row_fields = list(sdmx_feature_rows[0]['attributes'].keys())
   
        add_rows(sdmx_feature_rows, tbl, row_fields)

        if in_shouldjoin:
            unique_location_ids = []
            #for c in new_cases:
            #    for k in c.keys():
            #        if k == 'locationId':
            #            if not c[k] in unique_location_ids:
            #                unique_location_ids.append(c[k])


            # create cases FC table
            arcpy.SetProgressor('default', f'Creating {in_outputtablename} feature class with geographies ...')

            output_geofc_name = f'{in_outputtablename}_geo'
            if in_outputgeoname is not None:
                output_geofc_name = in_outputgeoname

            #err, fc_path = join_to_geo(tbl, fields, in_outworkspace, output_geofc_name, in_sdmxjoinfield, in_geolayer, in_geojoinfield, in_shouldkeepallgeo, unique_location_ids)
            #if err is not None:
            #    arcpy.AddError(err)
                        
            geo_fields_to_delete = []
            geo_fields_to_keep = []

            if in_geofieldmapping is not None and in_geofieldmapping.rowCount > 0:
                row_count = in_geofieldmapping.rowCount
                for i in range(row_count):
                    geo_fields_to_keep.append(in_geofieldmapping.getValue(i,0))

                for field in arcpy.Describe(in_geolayer).fields:
                    if field.name not in geo_fields_to_keep:
                        geo_fields_to_delete.append(field.name)

            fc_path = join_proper(tbl, fields, in_outworkspace, output_geofc_name, in_sdmxjoinfield, in_geolayer, in_geojoinfield, in_sdmxjoinfieldconversion, in_shouldkeepallgeo, geo_fields_to_delete)

            arcpy.SetParameter(len(parameters)-1, fc_path)
        else:           
            arcpy.SetParameter(len(parameters)-1, tbl)

        return
