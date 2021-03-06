import argparse
from Bio import SeqIO
from collections import defaultdict, OrderedDict
from collections import Counter

def parse_args():
    parser = argparse.ArgumentParser(description='Parse barcode info and seqkit bam TSV file, create report.')

    parser.add_argument("--tsv_file", action="store", type=str, dest="tsv_file")
    parser.add_argument("--annotated_reads", action="store", type=str, dest="reads")

    parser.add_argument("--report", action="store", type=str, dest="report")
    parser.add_argument("--sup_report", action="store", type=str, dest="sup_report")

    parser.add_argument("--reference_file", action="store", type=str, dest="references")
    parser.add_argument("--reference_options", action="store", type=str, dest="reference_options")

    parser.add_argument("--minimum_identity", default=0.8, action="store", type=float, dest="min_identity")

    return parser.parse_args()

def parse_reference_options(reference_options):
    #returns a dict of {key:list} pairs containing  
    # csv_header_to_be : list of corresponding read_header_group with optional coordinates
    # e.g. "genogroup" : [["genogroup"]]
    # e.g. "loc_genotype" : [["POL_genogroup",0,5000],["VP_genogroup",5000,7000]]
    columns = reference_options.split(";")
    ref_options = defaultdict(list)
    for i in columns:
        k,v = i.rstrip(']').split("[")
        v = [i.split(':') for i in v.split(",")]
        new_v =[]
        for sublist in v:
            if len(sublist)==3:
                new_v.append([sublist[0],int(sublist[1]),int(sublist[2])])
            else:
                new_v.append(sublist)
        ref_options[k]=new_v

    return ref_options, ','+','.join(ref_options.keys())


def parse_reference_file(references):
    #returns a dict of dicts containing reference header information
    #key is seq id i.e. first field of the header string
    ref_info = defaultdict(dict)
    for record in SeqIO.parse(references,"fasta"):
        tokens = record.description.split(' ')
        for i in tokens:
            try:
                info = i.split('=')
                ref_info[record.id][info[0]]=info[1]
                # ref_info['*'][info[0]]='NA'
            except:
                pass
    return ref_info

def parse_read_header(header):
    #returns a dict of {key:value} pairs containing all 
    #" key=value" strings present on the read header

    tokens= header.split(' ')
    header_info = {}
    for i in tokens:
        try:
            info = i.split('=')
            header_info[info[0]]=info[1]
        except:
            pass
    return header_info

def get_header_dict(reads):
    #This function parses the fastq file and returns a dictionary
    #with read name as the key and barcode information as the value
    # i.e. barcode_dict[read_name]=barcode

    header_dict = {}
    for record in SeqIO.parse(str(reads),"fastq"):
        header = parse_read_header(str(record.description))
        try:
            barcode = header["barcode"]
            start_time = header["start_time"]
        except:
            barcode = 'none'
            start_time = header["start_time"]

        header_dict[record.id]=(barcode, start_time)
    return header_dict

def check_overlap(coords1,coords2):
    list1 = list(range(coords1[0],coords1[1]))
    list2 = list(range(coords2[0],coords2[1]))
    overlap = set(list1).intersection(list2)
    if overlap:
        return True, len(overlap)
    else:
        return False, 0

def check_identity_threshold(mapping, min_identity):
    if float(min_identity)<1:
        min_id = float(min_identity)
    else:
        min_id = float(min_identity)/ 100
    if mapping["identity"] >= min_id:
        return True
    else:
        return False

SEQKIT_FIELDS = OrderedDict([
    ('Read', lambda x: ('read_name', x)),
    ('Ref', lambda x: ('ref_hit', x)),
    ('Pos', lambda x: ('coord_start', int(x))),
    ('EndPos', lambda x: ('coord_end', int(x))),
    ('MapQual', lambda x: ('MapQual', float(x))),
    ('Acc', lambda x: ('identity', float(x)/100.0)),
    ('ReadLen', lambda x: ('read_len', int(x))),
    ('RefLen', lambda x: ('ref_len', int(x))),
    ('RefAln', lambda x: ('aln_block_len', int(x))), # FIXME: not the block length
    ('RefCov', lambda x: ('RefCov', float(x))),
    ('ReadAln', lambda x: ('ReadAln', int(x))),
    ('ReadCov', lambda x: ('ReadCov', float(x))),
    ('Strand', lambda x: ("Strand",'+' if int(x) == 1 else '-')),
    ('MeanQual', lambda x: ('MeanQual', float(x))),
    ('LeftClip', lambda x: ('LeftClip', int(x))),
    ('RightClip', lambda x: ('RightClip', int(x))),
    ('Flags', lambda x: ('Flags', int(x))),
    ('IsSec', lambda x: ('IsSec', int(x))),
    ('IsSup', lambda x: ('IsSup', int(x))),
    ])

def parse_line(line, header_dict):
    values = OrderedDict()
    tokens = line.rstrip('\n').split('\t')

    # Parse seqkit BAM tsv output:
    for i, field in enumerate(SEQKIT_FIELDS.keys()):
        name, value = SEQKIT_FIELDS[field](tokens[i])
        values[name] = value
    if values["MapQual"] < 1:
        values["ref_hit"] = '?'
    values['query_start'] = values['LeftClip']
    values['query_end'] = values['read_len'] - values['RightClip']

    if values["read_name"] in header_dict:
        values["barcode"], values["start_time"] = header_dict[values["read_name"]] #if porechop didn't discard the read
    else:
        values["barcode"], values["start_time"] = "none", "?" #don't have info on time or barcode

    if values["ref_hit"] != "*":
        values["mismatches"] = '*' # FIXME
        values["matches"] = '*' # FIXME
    else:
        values["mismatches"] = 0
        values["mmatches"] = 0
        values["identity"]= 0

    return values


def write_mapping(report, mapping, reference_options, reference_info, counts, min_identity):
    if mapping["ref_hit"] == '*' or mapping["ref_hit"] == '?':
        # '*' means no mapping, '?' ambiguous mapping (i.e., multiple primary mappings)
        mapping['coord_start'], mapping['coord_end'] = 0, 0
        if (mapping["ref_hit"] == '*'):
            counts["unmapped"] += 1
        elif mapping['identity'] != 0.0:
            counts["ambiguous"] += 1

        if reference_options != None:
                mapping["ref_opts"] = []
                for k in reference_options:
                    mapping["ref_opts"].append(mapping["ref_hit"])
    else:
        if reference_options != None:
            mapping["ref_opts"] = []
            for k in reference_options:
                if len(reference_options[k]) == 1:
                    mapping["ref_opts"].append(reference_info[mapping["ref_hit"]][k])
                else:
                    overlap_list = []
                    for i in reference_options[k]:
                        if len(i) == 3:
                            sub_k, opt_start, opt_end = i
                            overlap, length = check_overlap((opt_start, opt_end),(int(mapping["coord_start"]), int(mapping["coord_end"])))
                            if overlap:
                                overlap_list.append((reference_info[mapping["ref_hit"]][sub_k], length))
                    if overlap_list:
                        best = sorted(overlap_list, key = lambda x : x[1], reverse=True)[0]
                        mapping["ref_opts"].append(best[0])
                    else:
                        mapping["ref_opts"].append("NA")

    

    if check_identity_threshold(mapping, min_identity):

        counts["total"] += 1 # FIXME: is this at the right place?

        mapping_length = mapping['aln_block_len']
        report.write(f"{mapping['read_name']},{mapping['read_len']},{mapping['start_time']},"
                    f"{mapping['barcode']},{mapping['ref_hit']},{mapping['ref_len']},"
                    f"{mapping['coord_start']},{mapping['coord_end']},{mapping['matches']},{mapping_length}")
        if 'ref_opts' in mapping:
            report.write(f",{','.join(mapping['ref_opts'])}\n")
        else:
            report.write("\n")
    else:
        counts["unmapped"] +=1
        report.write(f"{mapping['read_name']},{mapping['read_len']},{mapping['start_time']},"
                    f"{mapping['barcode']},*,0,0,0,0,0")
        if 'ref_opts' in mapping:
            ref_opt_list = ['*' for i in mapping['ref_opts']]
            report.write(f",{','.join(ref_opt_list)}\n")
        else:
            report.write("\n")


def write_sup_fields(mapping, sup_report, sup_fields):
    for i, f in enumerate(sup_fields):
        sep = ","
        if i == len(sup_fields)-1:
            sep = "\n"
        val = '*'
        if f in mapping:
            val = mapping[f]
        sup_report.write("{}{}".format(val, sep))

def parse_tsv(paf, report, sup_report, sup_fields, header_dict, reference_options, reference_info,min_identity):
    #This function parses the input paf file 
    #and outputs a csv report containing information relevant for RAMPART and barcode information
    # read_name,read_len,start_time,barcode,best_reference,start_coords,end_coords,ref_len,matches,aln_block_len,ref_option1,ref_option2
    counts = {
        "unmapped": 0,
        "ambiguous": 0,
        "total": 0
    }

    all_reads = { x:True for x in header_dict.keys()}
    with open(str(paf),"r") as f:
        last_mapping = None
        head_line = f.readline() # skip header
        for line in f:

            mapping = parse_line(line, header_dict)
            read_id = mapping["read_name"]
            if read_id in all_reads:
                del all_reads[read_id]

            if last_mapping:
                if mapping["read_name"] == last_mapping["read_name"]:
                    # this is another mapping for the same read so set the original one to ambiguous. Don't
                    # set last_mapping in case there is another mapping with the same read name.
                    last_mapping['ref_hit'] = '?'
                else:
                    write_mapping(report, last_mapping, reference_options, reference_info, counts,min_identity)
                    write_sup_fields(mapping, sup_report, sup_fields)
                    last_mapping = mapping
            else:
                last_mapping = mapping

        # write the last last_mapping
        write_mapping(report, last_mapping, reference_options, reference_info, counts,min_identity)
        write_sup_fields(mapping, sup_report, sup_fields)
        # Write unmapped reads:
        for r in all_reads.keys():
            rec = OrderedDict([('read_name', r), ('ref_hit', '*'), ('identity', 0.0)])
            rec['read_len'] = '*' # FIXME
            if rec["read_name"] in header_dict:
                rec["barcode"], rec["start_time"] = header_dict[rec["read_name"]]
            else:
                rec["barcode"], rec["start_time"] = "none", "?"
            rec['ref_hit'] = '*'
            rec['ref_len'] = '*'
            rec['coord_start'] = '*'
            rec['coord_end'] = '*'
            rec['matches'] = '*'
            rec['aln_block_len'] = '*'
            write_mapping(report, rec, reference_options, reference_info, counts,min_identity)
            write_sup_fields(mapping, sup_report, sup_fields)

    try:
        prop_unmapped = counts["unmapped"] / counts["total"]
        print("Proportion unmapped is {}".format(prop_unmapped))
        if prop_unmapped >0.95:
            print("\nWarning: Very few reads have mapped (less than 5%).\n")
    except:
        print("Probably can't find the records.") #division of zero the error

if __name__ == '__main__':

    args = parse_args()

    sup_csv_report = open(args.sup_report, "w")
    sup_fields = ["read_name", "ref_hit", "MapQual", "identity", "aln_block_len", "RefCov", "ReadAln", "ReadCov", "Strand", "MeanQual", "LeftClip", "RightClip","Flags"]
    with open(str(args.report), "w") as csv_report:
        if args.reference_options:
            reference_options,ref_option_header = parse_reference_options(args.reference_options)
            reference_info = parse_reference_file(args.references)
        else:
            reference_options,ref_option_header = None,''
            reference_info = None

        header_dict = get_header_dict(args.reads)

        csv_report.write(f"read_name,read_len,start_time,barcode,best_reference,ref_len,start_coords,end_coords,num_matches,mapping_len{ref_option_header}\n")
        for i, f in enumerate(sup_fields):
            sep = ","
            if i == len(sup_fields)-1:
                sep = "\n"
            sup_csv_report.write("{}{}".format(f,sep))
        parse_tsv(args.tsv_file, csv_report, sup_csv_report, sup_fields, header_dict, reference_options, reference_info,args.min_identity)
    sup_csv_report.flush()
    sup_csv_report.close()
